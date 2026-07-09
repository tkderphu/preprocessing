#! /bin/bash
# Setup document intelligence pipeline


sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release


sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
uv venv

uv pip install -p .venv/bin/python whisperx

uv init
uv add fastapi uvicorn python-multipart

cat << 'EOF' > main.py
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

app = FastAPI()

HF_TOKEN = os.getenv(
    "HF_TOKEN",
    "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"
)


@app.post("/transcribe")
async def transcribe(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    # Không dùng TemporaryDirectory()
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
        "--device", "cpu",
        "--output_dir", str(tmpdir),
    ]

    print("=" * 80)
    print("COMMAND:")
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

    print("=" * 80)
    print("RETURN CODE:", process.returncode)
    print("=" * 80)

    if process.returncode != 0:
        shutil.rmtree(tmpdir, ignore_errors=True)

        raise HTTPException(
            status_code=500,
            detail={
                "return_code": process.returncode,
                "logs": "".join(logs),
            },
        )

    txt_file = input_file.with_suffix(".txt")

    if not txt_file.exists():
        files = [p.name for p in tmpdir.iterdir()]

        shutil.rmtree(tmpdir, ignore_errors=True)

        raise HTTPException(
            status_code=500,
            detail={
                "message": "WhisperX did not generate txt file.",
                "generated_files": files,
                "logs": "".join(logs),
            },
        )

    print(f"TXT FILE: {txt_file}")

    # Xóa thư mục sau khi gửi file xong
    background_tasks.add_task(
        shutil.rmtree,
        tmpdir,
        ignore_errors=True,
    )

    return FileResponse(
        path=txt_file,
        filename=txt_file.name,
        media_type="text/plain",
        background=background_tasks,
    )
EOF

uv run uvicorn main:app --host 0.0.0.0 --port 8080