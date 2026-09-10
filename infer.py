import random
random.seed(42)
import argparse
import asyncio
from pathlib import Path

from TeleOCR.engine import aio_do_parse, do_parse
from TeleOCR.tools.read_file import read_fn
import TeleOCR.config as CONFIG


def parse_args():
    parser = argparse.ArgumentParser(
        description="TeleOCR batch inference"
    )

    parser.add_argument(
        "--image_sub_path",
        type=str,
        required=True,
        help="输入图片/PDF文件目录",
    )

    parser.add_argument(
        "--result_save_path",
        type=str,
        required=True,
        help="结果保存目录",
    )

    parser.add_argument(
        "--override",
        nargs="*",
        default=[],
        metavar="KEY=VALUE",
        help="运行时覆盖 TeleOCR 配置",
    )

    parser.add_argument(
        "--use_async",
        action="store_true",
        help="使用异步推理",
    )

    return parser.parse_args()

def get_image_paths(image_sub_path):
    return [
        path
        for path in image_sub_path.iterdir()
        if path.is_file()
        and path.suffix.lower() not in {".json", ".html"}
    ]

async def async_main(image_paths, result_save_path):
    for pdf_path in image_paths:
        print(f"\nProcessing: {pdf_path}")
        try:
            data = read_fn(pdf_path)
            await aio_do_parse(
                str(result_save_path),
                [pdf_path.stem],
                [data],
                valid_page_ids=[None],
            )
            print(
                f"Finished: {pdf_path.name}"
            )
        except Exception as e:
            print(
                f"Failed: {pdf_path.name}\n"
                f"Error: {e}"
            )

def sync_main(image_paths, result_save_path):
    for pdf_path in image_paths:

        print(f"\nProcessing: {pdf_path}")

        try:
            data = read_fn(pdf_path)

            do_parse(
                str(result_save_path),
                [pdf_path.stem],
                [data],
                valid_page_ids=[None],
            )
            print(
                f"Finished: {pdf_path.name}"
            )

        except Exception as e:

            print(
                f"Failed: {pdf_path.name}\n"
                f"Error: {e}"
            )

def main():

    args = parse_args()

    CONFIG.update(args.override)
    CONFIG.show()


    image_sub_path = Path(
        args.image_sub_path
    )

    result_save_path = Path(
        args.result_save_path
    )

    result_save_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    image_paths = get_image_paths(
        image_sub_path
    )

    print(
        f"Found {len(image_paths)} files."
    )

    if args.use_async:
        asyncio.run(
            async_main(
                image_paths,
                result_save_path,
            )
        )
    else:
        sync_main(
            image_paths,
            result_save_path,
        )


if __name__ == "__main__":
    main()