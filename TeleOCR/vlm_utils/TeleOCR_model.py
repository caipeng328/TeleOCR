import os
from .TeleOCR_client import TeleOCRClient
import TeleOCR.config as CONFIG


class TeleOCRMODEL:
    _instance = None
    _models = {}
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_model(
        self,
        backend: str,
        model_path: str | None,
        server_url: str | None,
        **kwargs,
    ) -> TeleOCRClient:
        print(backend, model_path, server_url)
        key = (backend, model_path, server_url)
        print(key not in self._models)
        if key not in self._models:
            model = None
            processor = None
            vllm_llm = None
            lmdeploy_engine = None
            vllm_async_llm = None
            batch_size = 0
            max_concurrency = 100
            http_timeout = 600
            server_headers = None
            max_retries = 3
            retry_backoff_factor = 0.5
            if os.getenv('OMP_NUM_THREADS') is None:
                os.environ["OMP_NUM_THREADS"] = "1"
            if backend == "transformers":
                if not model_path:
                    raise ValueError("model_path must be provided for the transformers backend.")
                try:
                    import torch
                    from transformers import AutoProcessor
                    try:
                        from transformers import AutoModelForImageTextToText as AutoModelClass
                    except ImportError:
                        try:
                            from transformers import AutoModelForVision2Seq as AutoModelClass
                        except ImportError:
                            from transformers import AutoModel as AutoModelClass
                except ImportError as exc:
                    raise ImportError("Please install torch and transformers to use the transformers backend.") from exc

                processor = AutoProcessor.from_pretrained(
                    model_path,
                    trust_remote_code=True,
                )
                torch_dtype = kwargs.pop(
                    "torch_dtype",
                    torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                )
                model = AutoModelClass.from_pretrained(
                    model_path,
                    trust_remote_code=True,
                    torch_dtype=torch_dtype,
                    **kwargs,
                )
                if torch.cuda.is_available():
                    model = model.cuda()
                model = model.eval()
            if backend == "vllm-engine":
                try:
                    import vllm
                except ImportError:
                    raise ImportError("Please install vllm to use the vllm-engine backend.")
                if "gpu_memory_utilization" not in kwargs:
                    kwargs["gpu_memory_utilization"] = CONFIG.GPU_MEMORY_UTILIZATION
                if "model" not in kwargs:
                    kwargs["model"] = model_path
                if "logits_processors" not in kwargs:
                    from . import TeleOCRLogitsProcessor
                    kwargs["logits_processors"] = [TeleOCRLogitsProcessor]
                if 'max_model_len' not in kwargs:
                    kwargs["max_model_len"] = CONFIG.MAX_MODEL_LEN
                vllm_llm = vllm.LLM(**kwargs)
            
            elif backend == "vllm-async-engine":
                try:
                    from vllm.engine.arg_utils import AsyncEngineArgs
                    from vllm.v1.engine.async_llm import AsyncLLM
                except ImportError:
                    raise ImportError("Please install vllm to use the vllm-async-engine backend.")
                
                if "gpu_memory_utilization" not in kwargs:
                    kwargs["gpu_memory_utilization"] = CONFIG.GPU_MEMORY_UTILIZATION
                
                if "model" not in kwargs:
                    kwargs["model"] = model_path
                
                if "logits_processors" not in kwargs:
                    from . import TeleOCRLogitsProcessor
                    kwargs["logits_processors"] = [TeleOCRLogitsProcessor]
            
                if 'max_model_len' not in kwargs:
                    kwargs["max_model_len"] = CONFIG.MAX_MODEL_LEN
                vllm_async_llm = AsyncLLM.from_engine_args(AsyncEngineArgs(**kwargs))
            
            self._models[key] = TeleOCRClient(
                backend=backend,
                model=model,
                processor=processor,
                lmdeploy_engine=lmdeploy_engine,
                vllm_llm=vllm_llm,
                vllm_async_llm=vllm_async_llm,
                server_url=server_url,
                batch_size=batch_size,
                max_concurrency=max_concurrency,
                http_timeout=http_timeout,
                server_headers=server_headers,
                max_retries=max_retries,
                retry_backoff_factor=retry_backoff_factor,
            )
        return self._models[key]


TeleOCRMODEL_SERVICE = TeleOCRMODEL()
