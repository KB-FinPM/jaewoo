from modules.pipeline import run_pipeline


if __name__ == "__main__":
    run_pipeline(
        docx_path="구축요건정의서.docx",
        output_dir="output",
        recreate_collection=True,
    )
