from pathlib import Path
import os
import shutil
import subprocess
import tempfile

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

app = FastAPI(title="WhisperX API")

HF_TOKEN = os.getenv("HF_TOKEN")
DEVICE = os.getenv("DEVICE", "cpu")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN environment variable is not set.")


@app.get("/")
def root():
    return {
        "message": "WhisperX API is running"
    }


@app.post("/transcribe")
async def transcribe(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    tmpdir = Path(tempfile.mkdtemp(prefix="whisperx_"))

    input_file = tmpdir / file.filename

    with open(input_file, "wb") as f:
        shutil.copyfileobj(file.file, f)

    cmd = [
        "whisperx",
        str(input_file),
        "--language", "vi",
        "--hf_token", HF_TOKEN,
        "--diarize",
        "--model", "large-v2",
        "--align_model", "WAV2VEC2_ASR_LARGE_LV60K_960H",
        "--compute_type", "int8",
        "--device", DEVICE,
        "--output_dir", str(tmpdir),
    ]

    print("=" * 80)
    print("Running command:")
    print(" ".join(cmd))
    print("=" * 80)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    logs = []

    for line in process.stdout:
        print(line, end="")
        logs.append(line)

    process.wait()

    if process.returncode != 0:
        shutil.rmtree(tmpdir, ignore_errors=True)

        raise HTTPException(
            status_code=500,
            detail={
                "return_code": process.returncode,
                "logs": "".join(logs)
            }
        )

    txt_file = input_file.with_suffix(".txt")

    if not txt_file.exists():
        files = [f.name for f in tmpdir.iterdir()]

        shutil.rmtree(tmpdir, ignore_errors=True)

        raise HTTPException(
            status_code=500,
            detail={
                "message": "TXT file not generated.",
                "generated_files": files,
                "logs": "".join(logs)
            }
        )

    background_tasks.add_task(
        shutil.rmtree,
        tmpdir,
        ignore_errors=True
    )

    return FileResponse(
        txt_file,
        filename=txt_file.name,
        media_type="text/plain",
        background=background_tasks
    )