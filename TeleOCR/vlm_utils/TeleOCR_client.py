import asyncio
import math
import re
from concurrent.futures import Executor
from typing import Literal, Sequence
import cv2
import time
from PIL import Image, ImageDraw
import numpy as np
from .post_process import post_process
from .structs import BLOCK_TYPES, ContentBlock
from .vlm_client import DEFAULT_SYSTEM_PROMPT, SamplingParams, new_vlm_client
from .vlm_client.utils import gather_tasks, get_png_bytes, get_rgb_image
import TeleOCR.config as CONFIG

class TeleOCRSamplingParams(SamplingParams):
    def __init__(
        self,
        temperature: float | None = 0.0,
        top_p: float | None = 0.01,
        top_k: int | None = 1,
        presence_penalty: float | None = 0.0,
        frequency_penalty: float | None = 0.0,
        repetition_penalty: float | None = 1.0,
        no_repeat_ngram_size: int | None = 100,
        max_new_tokens: int | None = None,
    ):
        super().__init__(
            temperature,
            top_p,
            top_k,
            presence_penalty, 
            frequency_penalty,
            repetition_penalty,
            no_repeat_ngram_size,
            max_new_tokens,
        )

LAYOUT_PROMPTS = {
    "Segmentation":"\nMulti-point Layout Segmentation Analysis.",
    "Detection":"\nAnalyze the image layout.",
}

DEFAULT_PROMPTS: dict[str, str] = {
    "text":"\nPlease output the text content from the image.",
    "table":"\nThis is the image of a table. Please output the table in OTSL format.",
    "equation":"\nPlease write out the expression of the formula in the image using LaTeX format.",
    "code":"\nThe image contains a code snippet, please output the parsing result.",
    "layout":"\nAnalyze the image layout.",
    "seal":"\nSeal Recognition:",
    "char":"\nThis is a scientific figure. Please extract the table implied by this figure.",
    "default":"\nPlease output the text content from the image.",
    "table_structure": "\nTable Recognition:",
    "formula_structure": "\nFormula Recognition:",
}

DEFAULT_SAMPLING_PARAMS: dict[str, SamplingParams] = {
    "text":TeleOCRSamplingParams(presence_penalty=1.0, frequency_penalty=0.05),
    "table":TeleOCRSamplingParams(presence_penalty=1.0, frequency_penalty=0.005),
    "equation":TeleOCRSamplingParams(presence_penalty=1.0, frequency_penalty=0.05),
    "code":TeleOCRSamplingParams(presence_penalty=1.0, frequency_penalty=0.05),
    "char":TeleOCRSamplingParams(presence_penalty=1.0, frequency_penalty=0.005),
    "layout":TeleOCRSamplingParams(),
    "seal":TeleOCRSamplingParams(presence_penalty=1.0, frequency_penalty=0.005),
    "default":TeleOCRSamplingParams(presence_penalty=1.0, frequency_penalty=0.05),
    "table_structure":TeleOCRSamplingParams(presence_penalty=1.0, frequency_penalty=0.005),
    "formula_structure":TeleOCRSamplingParams(presence_penalty=1.0, frequency_penalty=0.05),
}

ANGLE_MAPPING: dict[str, Literal[0, 90, 180, 270]] = {
    "up": 0,
    "right": 90,
    "down": 180,
    "left": 270,
}


def _parse_angle(tail: str) -> Literal[None, 0, 90, 180, 270]:
    for token, angle in ANGLE_MAPPING.items():
        if token in tail:
            return angle
    return None

def _convert_bbox(bbox: Sequence[int] | Sequence[str] | str, keep_four_numbers: bool = False,):
    if isinstance(bbox, str):
        bbox = list(map(int, bbox.split()))
    else:
        bbox = list(map(int, bbox))
    
    if len(bbox) < 4 or len(bbox) % 2 != 0:
        return None

    if any(coord < 0 or coord > 1000 for coord in bbox):
        return None
    padding_px = 0
    xs = bbox[0::2]
    ys = bbox[1::2]

    if keep_four_numbers:
        padding_bbox = [
            max(0, min(xs) - padding_px),
            max(0, min(ys) - padding_px),
            min(999, max(xs) + padding_px),
            min(999, max(ys) + padding_px),
        ]
    else:
        padding_bbox = []
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)

        for x, y in zip(xs, ys):
            if x == xmin:
                x = max(0, x - padding_px)
            elif x == xmax:
                x = min(999, x + padding_px)

            if y == ymin:
                y = max(0, y - padding_px)
            elif y == ymax:
                y = min(999, y + padding_px)

            padding_bbox.extend([x, y])

    return [num / 1000.0 for num in padding_bbox]

class TeleOCRClientHelper:
    def __init__(
        self,
        backend: str,
        prompts: dict[str, str],
        sampling_params: dict[str, SamplingParams],
        layout_image_size: tuple[int, int],
        min_image_edge: int,
        max_image_edge_ratio: float,
        simple_post_process: bool,
        handle_equation_block: bool,
        abandon_list: bool,
        abandon_paratext: bool,
        debug: bool,
        keep_four_numbers: bool,
    ) -> None:
        self.backend = backend
        self.prompts = prompts
        self.sampling_params = sampling_params
        self.layout_image_size = layout_image_size
        self.min_image_edge = min_image_edge
        self.max_image_edge_ratio = max_image_edge_ratio
        self.simple_post_process = simple_post_process
        self.handle_equation_block = handle_equation_block
        self.abandon_list = abandon_list
        self.abandon_paratext = abandon_paratext
        self.debug = debug

    def resize_by_need(self, image: Image.Image) -> Image.Image:
        edge_ratio = max(image.size) / min(image.size)
        if edge_ratio > self.max_image_edge_ratio:
            width, height = image.size
            if width > height:
                new_w, new_h = width, math.ceil(width / self.max_image_edge_ratio)
            else:
                new_w, new_h = math.ceil(height / self.max_image_edge_ratio), height
            new_image = Image.new(image.mode, (new_w, new_h), (255, 255, 255))
            new_image.paste(image, (int((new_w - width) / 2), int((new_h - height) / 2)))
            image = new_image
        if min(image.size) < self.min_image_edge:
            scale = self.min_image_edge / min(image.size)
            new_w, new_h = math.ceil(image.width * scale), math.ceil(image.height * scale)
            image = image.resize((new_w, new_h), Image.Resampling.BICUBIC)
        return image

    def prepare_for_layout(self, image: Image.Image) -> Image.Image | bytes:
        image = get_rgb_image(image)
        image = image.resize(self.layout_image_size, Image.Resampling.BICUBIC)
        if self.backend == "http-client":
            return get_png_bytes(image)
        return image

    def parse_layout_output(self, output: str) -> list[ContentBlock]:
        layout_re = re.compile(
            r'^<box:([\d\s]+)><label:(\w+)><([^>]+)>$'
        )
        blocks: list[ContentBlock] = []

        for line in output.split("\n"):
            line = line.strip()
            match = layout_re.match(line)
            if not match:
                print(f"Warning: line does not match layout format: {line}")
                continue
            box_nums, ref_type, tag = match.groups()
            
            ref_type = ref_type.lower()
            if ref_type not in BLOCK_TYPES:
                print(f"Warning: unknown block type in line: {ref_type}")
                continue
            
            box_list = _convert_bbox(box_nums)
            if box_list is None:
                print(f"Warning: unknown box {box_nums}")
                continue
            
            angle = _parse_angle(tag)
            if angle is None:
                print(f"Warning: no angle found in line: {line}")
            blocks.append(ContentBlock(ref_type, box_list, angle=angle))
            
        return blocks

    def prepare_for_extract(
        self,
        image: Image.Image,
        blocks: list[ContentBlock],
        not_extract_list: list[str] | None = None,
    ):
        image = get_rgb_image(image)

        width, height = image.size
        pixels = width * height
        if pixels > CONFIG.MAX_PIXELS:
            scale = (CONFIG.MAX_PIXELS / pixels) ** 0.5
            new_width = max(1, int(round(width * scale)))
            new_height = max(1, int(round(height * scale)))
            image = image.resize((new_width, new_height), Image.Resampling.BILINEAR)
        image_np = np.array(image)
        width, height = image.size
        block_images = []
        prompts = []
        sampling_params = []
        indices = []
        skip_list = {"image", "list", "equation_block"}
        if not_extract_list:
            for t in not_extract_list:
                if t in BLOCK_TYPES:
                    skip_list.add(t)
        for idx, block in enumerate(blocks):
            if block.type in skip_list:
                continue
            pts = np.array(block.bbox, dtype=np.float32).reshape(-1, 2)
            pts[:, 0] *= width
            pts[:, 1] *= height
            pts = pts.astype(np.int32)
            try:
                # -------- rectangle --------
                if len(pts) == 2:
                    x1, y1 = pts[0]
                    x2, y2 = pts[1]
                    crop = image.crop((x1, y1, x2, y2))
                # -------- polygon --------
                else:
                    x, y, w, h = cv2.boundingRect(pts)
                    crop_np = image_np[y:y+h, x:x+w]
                    mask = np.zeros((h, w), dtype=np.uint8)
                    pts_shift = pts.copy()
                    pts_shift[:, 0] -= x
                    pts_shift[:, 1] -= y
                    cv2.fillPoly(mask, [pts_shift], 255)
                    crop_np = cv2.bitwise_and(crop_np, crop_np, mask=mask)
                    crop = Image.fromarray(crop_np)
            except:
                continue
            
            if crop.width < 1 or crop.height < 1:
                print("Warning: invalid crop size")
                continue
            if block.angle in [90, 180, 270]:
                crop = crop.rotate(block.angle, expand=True)
            crop = self.resize_by_need(crop)
            if self.backend == "http-client":
                crop = get_png_bytes(crop)
            block_images.append(crop)
            prompt = self.prompts.get(block.type) or self.prompts["default"]
            prompts.append(prompt)
            params = (
                self.sampling_params.get(block.type)
                or self.sampling_params.get("default")
            )
            sampling_params.append(params)
            indices.append(idx)
        return block_images, prompts, sampling_params, indices
    
    def post_process(self, blocks: list[ContentBlock]) -> list[ContentBlock]:
        try:
            
            return post_process(
                blocks,
                simple_post_process=self.simple_post_process,
                handle_equation_block=self.handle_equation_block,
                abandon_list=self.abandon_list,
                abandon_paratext=self.abandon_paratext,
                debug=self.debug,
            )
        except Exception as e:
            print(f"Warning: post-processing failed with error: {e}")
            return blocks

    def batch_prepare_for_layout(
        self,
        executor: Executor | None,
        images: list[Image.Image],
    ) -> list[Image.Image | bytes]:
        if executor is None:
            return [self.prepare_for_layout(im) for im in images]
        return list(executor.map(self.prepare_for_layout, images))

    def batch_parse_layout_output(
        self,
        executor: Executor | None,
        outputs: list[str],
    ) -> list[list[ContentBlock]]:
        if executor is None:
            return [self.parse_layout_output(output) for output in outputs]
        return list(executor.map(self.parse_layout_output, outputs))

    def batch_prepare_for_extract(
        self,
        executor: Executor | None,
        images: list[Image.Image],
        blocks_list: list[list[ContentBlock]],
        not_extract_list: list[str] | None = None,
    ) -> list[tuple[list[Image.Image | bytes], list[str], list[SamplingParams | None], list[int]]]:
        if executor is None:
            return [self.prepare_for_extract(im, bls, not_extract_list) for im, bls in zip(images, blocks_list)]
        return list(executor.map(self.prepare_for_extract, images, blocks_list, [not_extract_list] * len(images)))

    def batch_post_process(
        self,
        executor: Executor | None,
        blocks_list: list[list[ContentBlock]],
    ) -> list[list[ContentBlock]]:
        if executor is None:
            return [self.post_process(blocks) for blocks in blocks_list]
        return list(executor.map(self.post_process, blocks_list))

    async def aio_prepare_for_layout(
        self,
        executor: Executor | None,
        image: Image.Image,
    ) -> Image.Image | bytes:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.prepare_for_layout, image)

    async def aio_parse_layout_output(
        self,
        executor: Executor | None,
        output: str,
    ) -> list[ContentBlock]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.parse_layout_output, output)

    async def aio_prepare_for_extract(
        self,
        executor: Executor | None,
        image: Image.Image,
        blocks: list[ContentBlock],
        not_extract_list: list[str] | None = None,
    ) -> tuple[list[Image.Image | bytes], list[str], list[SamplingParams | None], list[int]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.prepare_for_extract, image, blocks, not_extract_list)

    async def aio_post_process(
        self,
        executor: Executor | None,
        blocks: list[ContentBlock],
    ) -> list[ContentBlock]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.post_process, blocks)


class TeleOCRClient:
    def __init__(
        self,
        backend: Literal[
            "http-client",
            "transformers",
            "mlx-engine",
            "lmdeploy-engine",
            "vllm-engine",
            "vllm-async-engine",
        ],
        model_name: str | None = None,
        server_url: str | None = None,
        server_headers: dict[str, str] | None = None,
        model=None,  # transformers model
        processor=None,  # transformers processor
        vllm_llm=None,  # vllm.LLM model
        vllm_async_llm=None,  # vllm.v1.engine.async_llm.AsyncLLM instance
        lmdeploy_engine=None,  # lmdeploy.serve.vl_async_engine.VLAsyncEngine instance
        model_path: str | None = None,
        prompts: dict[str, str] = DEFAULT_PROMPTS,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        sampling_params: dict[str, SamplingParams] = DEFAULT_SAMPLING_PARAMS,
        layout_image_size: tuple[int, int] = (1036, 1036),
        min_image_edge: int = 28,
        max_image_edge_ratio: float = 50,
        simple_post_process: bool = False,
        handle_equation_block: bool = True,
        abandon_list: bool = False,
        keep_four_numbers: bool = True,
        abandon_paratext: bool = False,
        incremental_priority: bool = False,
        max_concurrency: int = 100,
        executor: Executor | None = None,
        batch_size: int = 0,  # for transformers and vllm-engine
        http_timeout: int = 600,  # for http-client backend only
        connect_timeout: int = 10,  # for http-client backend only
        max_connections: int | None = None,  # for http-client backend only
        max_keepalive_connections: int | None = 20,  # for http-client backend only
        keepalive_expiry: float | None = 5,  # for http-client backend only
        use_tqdm: bool = True,
        debug: bool = False,
        max_retries: int = 3,  # for http-client backend only
        retry_backoff_factor: float = 0.5,  # for http-client backend only
    ) -> None:
        if backend == "lmdeploy-engine":
            if lmdeploy_engine is None:
                if not model_path:
                    raise ValueError("model_path must be provided when lmdeploy_engine is None.")

                try:
                    # from lmdeploy import pipeline
                    from lmdeploy.serve.vl_async_engine import VLAsyncEngine
                except ImportError:
                    raise ImportError("Please install lmdeploy to use the lmdeploy-engine backend.")

                lmdeploy_engine = VLAsyncEngine(
                    model_path,
                )

        if backend == "vllm-engine":
            if vllm_llm is None:
                if not model_path:
                    raise ValueError("model_path must be provided when vllm_llm is None.")

                try:
                    import vllm
                except ImportError:
                    raise ImportError("Please install vllm to use the vllm-engine backend.")

                vllm_llm = vllm.LLM(model_path)

        elif backend == "vllm-async-engine":
            if vllm_async_llm is None:
                if not model_path:
                    raise ValueError("model_path must be provided when vllm_async_llm is None.")

                try:
                    from vllm.engine.arg_utils import AsyncEngineArgs
                    from vllm.v1.engine.async_llm import AsyncLLM
                except ImportError:
                    raise ImportError("Please install vllm to use the vllm-async-engine backend.")

                vllm_async_llm = AsyncLLM.from_engine_args(AsyncEngineArgs(model_path))

        self.client = new_vlm_client(
            backend=backend,
            model_name=model_name,
            server_url=server_url,
            server_headers=server_headers,
            model=model,
            processor=processor,
            lmdeploy_engine=lmdeploy_engine,
            vllm_llm=vllm_llm,
            vllm_async_llm=vllm_async_llm,
            system_prompt=system_prompt,
            allow_truncated_content=True,
            max_concurrency=max_concurrency,
            batch_size=batch_size,
            http_timeout=http_timeout,
            connect_timeout=connect_timeout,
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            use_tqdm=use_tqdm,
            debug=debug,
            max_retries=max_retries,
            retry_backoff_factor=retry_backoff_factor,
        )
        self.helper = TeleOCRClientHelper(
            backend=backend,
            prompts=prompts,
            sampling_params=sampling_params,
            layout_image_size=layout_image_size,
            min_image_edge=min_image_edge,
            max_image_edge_ratio=max_image_edge_ratio,
            simple_post_process=simple_post_process,
            handle_equation_block=handle_equation_block,
            abandon_list=abandon_list,
            abandon_paratext=abandon_paratext,
            debug=debug,
            keep_four_numbers=keep_four_numbers,
        )
        self.backend = backend
        self.prompts = prompts
        self.sampling_params = sampling_params
        self.incremental_priority = incremental_priority
        self.max_concurrency = max_concurrency
        self.executor = executor
        self.use_tqdm = use_tqdm
        self.debug = debug

        if backend in ("vllm-async-engine", "lmdeploy-engine"):
            self.batching_mode = "concurrent"
        else:  # backend in ("transformers", "vllm-engine")
            self.batching_mode = "stepping"

    def layout_detect(
        self,
        image: Image.Image,
        priority: int | None = None,
    ) -> list[ContentBlock]:
        layout_image = self.helper.prepare_for_layout(image)
        prompt = LAYOUT_PROMPTS.get(CONFIG.LAYOUT_MODE) or self.prompts["layout"]
        params = self.sampling_params.get("layout") or self.sampling_params.get("default")
        output = self.client.predict(layout_image, prompt, params, priority)
        return self.helper.parse_layout_output(output)
    
    def block_parse( 
        self,
        image: Image.Image,
        task: str | None,
    ):
        prompt = self.prompts.get(task) or self.prompts["default"]
        params = self.sampling_params.get(task) or self.sampling_params.get("default")
        outputs = self.client.predict(image, prompt, params)
        return outputs


    def batch_layout_detect(
        self,
        images: list[Image.Image],
        priority: Sequence[int | None] | int | None = None,
    ) -> list[list[ContentBlock]]:
        if priority is None and self.incremental_priority:
            priority = list(range(len(images)))
        layout_images = self.helper.batch_prepare_for_layout(self.executor, images)
        prompt = LAYOUT_PROMPTS.get(CONFIG.LAYOUT_MODE) or self.prompts["layout"]
        params = self.sampling_params.get("layout") or self.sampling_params.get("default")
        outputs = self.client.batch_predict(layout_images, prompt, params, priority)
        return self.helper.batch_parse_layout_output(self.executor, outputs)

    async def aio_layout_detect(
        self,
        image: Image.Image,
        priority: int | None = None,
        semaphore: asyncio.Semaphore | None = None,
    ) -> list[ContentBlock]:

        # aio_prepare_for_layout_time = time.time()
        layout_image = await self.helper.aio_prepare_for_layout(self.executor, image)
        # print(f'aio_prepare_for_layout is {time.time() - aio_prepare_for_layout_time}')
        
        # aio_predict_time = time.time()
        prompt = LAYOUT_PROMPTS.get(CONFIG.LAYOUT_MODE) or self.prompts["layout"]
        params = self.sampling_params.get("layout") or self.sampling_params.get("default")
        if semaphore is None:
            output = await self.client.aio_predict(layout_image, prompt, params, priority)
        else:
            async with semaphore:
                output = await self.client.aio_predict(layout_image, prompt, params, priority)
        # print(f'aio_predict_time is {time.time() - aio_predict_time}')
        
        # aio_parse_layout_output_time = time.time()
        result = await self.helper.aio_parse_layout_output(self.executor, output)
        # print(f'aio_parse_layout_output_time is {time.time() - aio_parse_layout_output_time}')
        return result

    async def aio_batch_layout_detect(
        self,
        images: list[Image.Image],
        priority: Sequence[int | None] | int | None = None,
        semaphore: asyncio.Semaphore | None = None,
    ) -> list[list[ContentBlock]]:
        if priority is None and self.incremental_priority:
            priority = list(range(len(images)))
        semaphore = semaphore or asyncio.Semaphore(self.max_concurrency)
        layout_images = await gather_tasks(
            tasks=[self.helper.aio_prepare_for_layout(self.executor, im) for im in images],
            use_tqdm=self.use_tqdm,
            tqdm_desc="Layout Preparation",
        )
        prompt = LAYOUT_PROMPTS.get(CONFIG.LAYOUT_MODE) or self.prompts["layout"]
        params = self.sampling_params.get("layout") or self.sampling_params.get("default")
        outputs = await self.client.aio_batch_predict(
            layout_images,
            prompt,
            params,
            priority,
            semaphore=semaphore,
            use_tqdm=self.use_tqdm,
            tqdm_desc="Layout Detection",
        )
        return await gather_tasks(
            tasks=[self.helper.aio_parse_layout_output(self.executor, out) for out in outputs],
            use_tqdm=self.use_tqdm,
            tqdm_desc="Layout Output Parsing",
        )


    def content_extract(
        self,
        image: Image.Image,
        type: str = "text",
        priority: int | None = None,
    ) -> str | None:
        blocks = [ContentBlock(type, [0.0, 0.0, 1.0, 1.0])]
        block_images, prompts, params, _ = self.helper.prepare_for_extract(image, blocks)
        if not (block_images and prompts and params):
            return None
        output = self.client.predict(block_images[0], prompts[0], params[0], priority)
        blocks[0].content = output
        blocks = self.helper.post_process(blocks)
        return blocks[0].content if blocks else None


    def batch_content_extract(
        self,
        images: list[Image.Image],
        types: Sequence[str] | str = "text",
        priority: Sequence[int | None] | int | None = None,
    ) -> list[str | None]:
        if isinstance(types, str):
            types = [types] * len(images)
        if len(types) != len(images):
            raise Exception("Length of types must match length of images")
        if priority is None and self.incremental_priority:
            priority = list(range(len(images)))
        blocks_list = [[ContentBlock(type, [0.0, 0.0, 1.0, 1.0])] for type in types]
        all_images: list[Image.Image | bytes] = []
        all_prompts: list[str] = []
        all_params: list[SamplingParams | None] = []
        all_indices: list[tuple[int, int]] = []
        prepared_inputs = self.helper.batch_prepare_for_extract(self.executor, images, blocks_list)
        for img_idx, (block_images, prompts, params, indices) in enumerate(prepared_inputs):
            all_images.extend(block_images)
            all_prompts.extend(prompts)
            all_params.extend(params)
            all_indices.extend([(img_idx, idx) for idx in indices])
        outputs = self.client.batch_predict(all_images, all_prompts, all_params, priority)
        for (img_idx, idx), output in zip(all_indices, outputs):
            blocks_list[img_idx][idx].content = output
        blocks_list = self.helper.batch_post_process(self.executor, blocks_list)
        return [blocks[0].content if blocks else None for blocks in blocks_list]


    async def aio_content_extract(
        self,
        image: Image.Image,
        type: str = "text",
        priority: int | None = None,
        semaphore: asyncio.Semaphore | None = None,
    ) -> str | None:
        blocks = [ContentBlock(type, [0.0, 0.0, 1.0, 1.0])]
        block_images, prompts, params, _ = await self.helper.aio_prepare_for_extract(self.executor, image, blocks)
        if not (block_images and prompts and params):
            return None
        if semaphore is None:
            output = await self.client.aio_predict(block_images[0], prompts[0], params[0], priority)
        else:
            async with semaphore:
                output = await self.client.aio_predict(block_images[0], prompts[0], params[0], priority)
        blocks[0].content = output
        blocks = await self.helper.aio_post_process(self.executor, blocks)
        return blocks[0].content if blocks else None


    async def aio_batch_content_extract(
        self,
        images: list[Image.Image],
        types: Sequence[str] | str = "text",
        priority: Sequence[int | None] | int | None = None,
        semaphore: asyncio.Semaphore | None = None,
    ) -> list[str | None]:
        if isinstance(types, str):
            types = [types] * len(images)
        if len(types) != len(images):
            raise Exception("Length of types must match length of images")
        if priority is None and self.incremental_priority:
            priority = list(range(len(images)))
        semaphore = semaphore or asyncio.Semaphore(self.max_concurrency)
        blocks_list = [[ContentBlock(type, [0.0, 0.0, 1.0, 1.0])] for type in types]
        all_images: list[Image.Image | bytes] = []
        all_prompts: list[str] = []
        all_params: list[SamplingParams | None] = []
        all_indices: list[tuple[int, int]] = []
        prepared_inputs = await gather_tasks(
            tasks=[self.helper.aio_prepare_for_extract(self.executor, *args) for args in zip(images, blocks_list)],
            use_tqdm=self.use_tqdm,
            tqdm_desc="Extract Preparation",
        )
        for img_idx, (block_images, prompts, params, indices) in enumerate(prepared_inputs):
            all_images.extend(block_images)
            all_prompts.extend(prompts)
            all_params.extend(params)
            all_indices.extend([(img_idx, idx) for idx in indices])
        outputs = await self.client.aio_batch_predict(
            all_images,
            all_prompts,
            all_params,
            priority,
            semaphore=semaphore,
            use_tqdm=self.use_tqdm,
            tqdm_desc="Extraction",
        )
        for (img_idx, idx), output in zip(all_indices, outputs):
            blocks_list[img_idx][idx].content = output
        blocks_list = await gather_tasks(
            tasks=[self.helper.aio_post_process(self.executor, blocks) for blocks in blocks_list],
            use_tqdm=self.use_tqdm,
            tqdm_desc="Post Processing",
        )
        return [blocks[0].content if blocks else None for blocks in blocks_list]


    def two_step_extract(
        self,
        image: Image.Image,
        priority: int | None = None,
        not_extract_list: list[str] | None = None,
    ) -> list[ContentBlock]:
        blocks = self.layout_detect(image, priority)
        block_images, prompts, params, indices = self.helper.prepare_for_extract(image, blocks, not_extract_list)
        outputs = self.client.batch_predict(block_images, prompts, params, priority)
        for idx, output in zip(indices, outputs):
            blocks[idx].content = output
        return self.helper.post_process(blocks)

    async def aio_two_step_extract(
        self,
        image: Image.Image,
        priority: int | None = None,
        semaphore: asyncio.Semaphore | None = None,
        not_extract_list: list[str] | None = None,
    ) -> list[ContentBlock]:
        semaphore = semaphore or asyncio.Semaphore(self.max_concurrency)
        
        aio_layout_detect_time = time.time()
        blocks = await self.aio_layout_detect(image, priority, semaphore)
        # print(f'aio_layout_detect_time is {time.time() - aio_layout_detect_time}')
    
        block_images, prompts, params, indices = await self.helper.aio_prepare_for_extract(
            self.executor,
            image,
            blocks,
            not_extract_list, 
        )


        outputs = await self.client.aio_batch_predict(block_images, prompts, params, priority, semaphore=semaphore)
        
        for idx, output in zip(indices, outputs):
            blocks[idx].content = output
        result = await self.helper.aio_post_process(self.executor, blocks)
        return result

    def concurrent_two_step_extract(
        self,
        images: list[Image.Image],
        priority: Sequence[int | None] | int | None = None,
        not_extract_list: list[str] | None = None,
    ) -> list[list[ContentBlock]]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        task = self.aio_concurrent_two_step_extract(images, priority, not_extract_list)

        if loop is not None:
            return loop.run_until_complete(task)
        else:
            return asyncio.run(task)

    async def aio_concurrent_two_step_extract(
        self,
        images: list[Image.Image],
        priority: Sequence[int | None] | int | None = None,
        not_extract_list: list[str] | None = None,
        semaphore: asyncio.Semaphore | None = None,
    ) -> list[list[ContentBlock]]:
        if priority is None and self.incremental_priority:
            priority = list(range(len(images)))
        if not isinstance(priority, Sequence):
            priority = [priority] * len(images)
        semaphore = semaphore or asyncio.Semaphore(self.max_concurrency)
        return await gather_tasks(
            tasks=[self.aio_two_step_extract(*args, semaphore, not_extract_list) for args in zip(images, priority)],
            use_tqdm=self.use_tqdm,
            tqdm_desc="Two Step Extraction",
        )


    def stepping_two_step_extract(
        self,
        images: list[Image.Image],
        priority: Sequence[int | None] | int | None = None,
        not_extract_list: list[str] | None = None,
    ) -> list[list[ContentBlock]]:
        if priority is None and self.incremental_priority:
            priority = list(range(len(images)))
        # 布局检测
        blocks_list = self.batch_layout_detect(images, priority)
        all_images: list[Image.Image | bytes] = []
        all_prompts: list[str] = []
        all_params: list[SamplingParams | None] = []
        all_indices: list[tuple[int, int]] = []
        # The code snippet `prepared_inputs` is not a valid Python code. It seems like a placeholder
        # or a comment. It does not perform any specific action or operation in Python.
        # The code snippet `prepared_inputs` is not a valid Python code. It seems to be a placeholder
        # or a comment. It does not perform any specific action or operation in Python.
        prepared_inputs = self.helper.batch_prepare_for_extract(
            self.executor,
            images,
            blocks_list,
            not_extract_list,
        )
        for img_idx, (block_images, prompts, params, indices) in enumerate(prepared_inputs):
            all_images.extend(block_images)
            all_prompts.extend(prompts)
            all_params.extend(params)
            all_indices.extend([(img_idx, idx) for idx in indices])
        outputs = self.client.batch_predict(all_images, all_prompts, all_params, priority)
        for (img_idx, idx), output in zip(all_indices, outputs):
            blocks_list[img_idx][idx].content = output
        return self.helper.batch_post_process(self.executor, blocks_list)

    async def aio_stepping_two_step_extract(
        self,
        images: list[Image.Image],
        priority: Sequence[int | None] | int | None = None,
        not_extract_list: list[str] | None = None,
        semaphore: asyncio.Semaphore | None = None,
    ) -> list[list[ContentBlock]]:
        if priority is None and self.incremental_priority:
            priority = list(range(len(images)))
        semaphore = semaphore or asyncio.Semaphore(self.max_concurrency)
        blocks_list = await self.aio_batch_layout_detect(images, priority, semaphore)
        all_images: list[Image.Image | bytes] = []
        all_prompts: list[str] = []
        all_params: list[SamplingParams | None] = []
        all_indices: list[tuple[int, int]] = []
        prepared_inputs = await gather_tasks(
            tasks=[
                self.helper.aio_prepare_for_extract(
                    self.executor,
                    *args,
                    not_extract_list,
                )
                for args in zip(images, blocks_list)
            ],
            use_tqdm=self.use_tqdm,
            tqdm_desc="Extract Preparation",
        )
        for img_idx, (block_images, prompts, params, indices) in enumerate(prepared_inputs):
            all_images.extend(block_images)
            all_prompts.extend(prompts)
            all_params.extend(params)
            all_indices.extend([(img_idx, idx) for idx in indices])
        outputs = await self.client.aio_batch_predict(
            all_images,
            all_prompts,
            all_params,
            priority,
            semaphore=semaphore,
            use_tqdm=self.use_tqdm,
            tqdm_desc="Extraction",
        )
        for (img_idx, idx), output in zip(all_indices, outputs):
            blocks_list[img_idx][idx].content = output
        return await gather_tasks(
            tasks=[self.helper.aio_post_process(self.executor, blocks) for blocks in blocks_list],
            use_tqdm=self.use_tqdm,
            tqdm_desc="Post Processing",
        )

    def batch_two_step_extract(
        self,
        images: list[Image.Image],
        priority: Sequence[int | None] | int | None = None,
        not_extract_list: list[str] | None = None,
    ) -> list[list[ContentBlock]]:
        if self.batching_mode == "concurrent":
            return self.concurrent_two_step_extract(images, priority, not_extract_list)
        else:  # self.batching_mode == "stepping"
            return self.stepping_two_step_extract(images, priority, not_extract_list)

    async def aio_batch_two_step_extract(
        self,
        images: list[Image.Image],
        priority: Sequence[int | None] | int | None = None,
        not_extract_list: list[str] | None = None,
        semaphore: asyncio.Semaphore | None = None,
    ) -> list[list[ContentBlock]]:
        semaphore = semaphore or asyncio.Semaphore(self.max_concurrency)
        if self.batching_mode == "concurrent":
            return await self.aio_concurrent_two_step_extract(images, priority, not_extract_list, semaphore)
        else:  # self.batching_mode == "stepping"
            return await self.aio_stepping_two_step_extract(images, priority, not_extract_list, semaphore)
