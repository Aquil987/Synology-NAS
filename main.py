from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi import Query, HTTPException
from typing import List
import httpx

app = FastAPI(title="Synology NAS Test API")

SYNOLOGY_BASE_URL = "Base URL"
SYNOLOGY_USERNAME = "your-user-name"
SYNOLOGY_PASSWORD = "your-password"

DEFAULT_ROOT_FOLDER = "/base-directory"

synology_session = {
    "sid": None
}


async def clear_synology_sid():
    synology_session["sid"] = None


async def synology_login() -> str:
    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            response = await client.post(
                f"{SYNOLOGY_BASE_URL}/webapi/auth.cgi",
                data={
                    "api": "SYNO.API.Auth",
                    "version": "6",
                    "method": "login",
                    "account": SYNOLOGY_USERNAME,
                    "passwd": SYNOLOGY_PASSWORD,
                    "session": "FileStation",
                    "format": "sid",
                },
            )

        data = response.json()

        if not data.get("success"):
            raise HTTPException(
                status_code=401,
                detail={
                    "message": "Synology login failed",
                    "synology_response": data,
                },
            )

        sid = data.get("data", {}).get("sid")

        if not sid:
            raise HTTPException(
                status_code=401,
                detail="Synology login succeeded but SID was not returned",
            )

        return sid

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to connect to Synology NAS: {str(e)}",
        )


async def get_synology_sid() -> str:
    if synology_session["sid"]:
        return synology_session["sid"]

    sid = await synology_login()
    synology_session["sid"] = sid
    return sid


async def synology_logout(sid: str):
    if not sid:
        return

    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            await client.post(
                f"{SYNOLOGY_BASE_URL}/webapi/auth.cgi",
                data={
                    "api": "SYNO.API.Auth",
                    "version": "6",
                    "method": "logout",
                    "session": "FileStation",
                    "_sid": sid,
                },
            )

    except httpx.RequestError:
        pass


async def create_folder(folder_path: str):
    sid = await get_synology_sid()

    folder_path = folder_path.rstrip("/")

    if not folder_path.startswith("/"):
        raise HTTPException(
            status_code=400,
            detail="Folder path must start with /",
        )

    parent_path = "/".join(folder_path.split("/")[:-1])
    folder_name = folder_path.split("/")[-1]

    if not parent_path:
        parent_path = "/"

    try:
        async with httpx.AsyncClient(verify=False, timeout=60) as client:
            response = await client.post(
                f"{SYNOLOGY_BASE_URL}/webapi/entry.cgi",
                data={
                    "api": "SYNO.FileStation.CreateFolder",
                    "version": "2",
                    "method": "create",
                    "folder_path": parent_path,
                    "name": folder_name,
                    "force_parent": "true",
                    "_sid": sid,
                },
            )

        data = response.json()

        if data.get("success"):
            return data

        await clear_synology_sid()

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to create folder on Synology NAS",
                "folder_path": folder_path,
                "synology_response": data,
            },
        )

    except httpx.RequestError as e:
        await clear_synology_sid()
        raise HTTPException(
            status_code=503,
            detail=f"Synology NAS request failed: {str(e)}",
        )


async def upload_file_to_nas(file: UploadFile, destination_folder: str):
    sid = await get_synology_sid()

    if not destination_folder.startswith("/"):
        raise HTTPException(
            status_code=400,
            detail="Destination folder must start with /",
        )

    try:
        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        async with httpx.AsyncClient(verify=False, timeout=120) as client:
            response = await client.post(
                f"{SYNOLOGY_BASE_URL}/webapi/entry.cgi",
                params={
                    "_sid": sid,
                },
                data={
                    "api": "SYNO.FileStation.Upload",
                    "version": "2",
                    "method": "upload",
                    "path": destination_folder,
                    "create_parents": "true",
                    "overwrite": "true",
                },
                files={
                    "file": (
                        file.filename,
                        file_bytes,
                        file.content_type or "application/octet-stream",
                    )
                },
            )

        data = response.json()

        if data.get("success"):
            return data

        # await clear_synology_sid()

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to upload file to Synology NAS",
                "destination_folder": destination_folder,
                "filename": file.filename,
                "synology_response": data,
            },
        )

    except HTTPException:
        raise

    except httpx.RequestError as e:
        await clear_synology_sid()
        raise HTTPException(
            status_code=503,
            detail=f"Synology NAS request failed: {str(e)}",
        )

    except Exception as e:
        await clear_synology_sid()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected upload error: {str(e)}",
        )


@app.get("/nas/login-test")
async def login_test():
    sid = await synology_login()
    synology_session["sid"] = sid

    return {
        "message": "Synology login successful",
        "sid_cached": True,
    }


@app.post("/nas/logout")
async def logout():
    sid = synology_session.get("sid")

    if sid:
        await synology_logout(sid)

    await clear_synology_sid()

    return {
        "message": "Synology session cleared successfully"
    }


@app.post("/nas/create-folder")
async def test_create_folder(folder_path: str = Form(...)):
    result = await create_folder(folder_path)

    return {
        "message": "Folder created successfully",
        "folder_path": folder_path,
        "result": result,
    }


@app.post("/nas/upload/direct")
async def upload_direct_file(file: UploadFile = File(...)):
    destination = f"{DEFAULT_ROOT_FOLDER}/a53af076-fbec-431f-a4a4-1371297bf3f2/education-details"

    result = await upload_file_to_nas(file, destination)

    return {
        "message": "Direct file uploaded successfully",
        "destination": destination,
        "filename": file.filename,
        "result": result,
    }


@app.post("/nas/upload/multiple")
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    destination = f"{DEFAULT_ROOT_FOLDER}/multiple-upload"

    uploaded_files = []

    for file in files:
        result = await upload_file_to_nas(file, destination)

        uploaded_files.append({
            "filename": file.filename,
            "destination": destination,
            "final_path": f"{destination}/{file.filename}",
            "result": result,
        })

    return {
        "message": "Multiple files uploaded successfully",
        "files": uploaded_files,
    }


@app.post("/nas/upload/nested")
async def upload_nested_file(file: UploadFile = File(...)):
    destination = f"{DEFAULT_ROOT_FOLDER}/Aquil/document"

    result = await upload_file_to_nas(file, destination)

    return {
        "message": "Nested file uploaded successfully",
        "destination": destination,
        "final_path": f"{destination}/{file.filename}",
        "result": result,
    }


@app.post("/nas/upload/custom")
async def upload_custom_file(
    destination_folder: str = Form(...),
    file: UploadFile = File(...),
):
    result = await upload_file_to_nas(file, destination_folder)

    return {
        "message": "Custom file uploaded successfully",
        "destination": destination_folder,
        "final_path": f"{destination_folder}/{file.filename}",
        "result": result,
    }

def get_media_type(filename: str) -> str:
    ext = filename.lower().split(".")[-1]

    media_types = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "txt": "text/plain",
        "csv": "text/csv",
    }

    return media_types.get(ext, "application/octet-stream")


async def get_synology_stream_client(file_path: str):
    sid = await get_synology_sid()
    client = httpx.AsyncClient(verify=False, timeout=None)

    try:
        request = client.build_request(
            "GET",
            f"{SYNOLOGY_BASE_URL}/webapi/entry.cgi",
            params={
                "api": "SYNO.FileStation.Download",
                "version": "2",
                "method": "download",
                "path": file_path,
                "mode": "open",
                "_sid": sid,
            },
        )

        response = await client.send(request, stream=True)

        content_type = response.headers.get("content-type", "")

        if response.status_code != 200 or "application/json" in content_type:
            body = await response.aread()
            await response.aclose()
            await client.aclose()
            await clear_synology_sid()

            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Failed to stream file from Synology NAS",
                    "file_path": file_path,
                    "synology_status_code": response.status_code,
                    "synology_response": body.decode(errors="ignore"),
                },
            )

        return client, response

    except HTTPException:
        raise

    except Exception as e:
        await client.aclose()
        await clear_synology_sid()
        raise HTTPException(
            status_code=500,
            detail=f"Synology stream request failed: {str(e)}",
        )
    
from urllib.parse import urlparse, unquote
def normalize_nas_file_path(file_path: str) -> str:
    file_path = unquote(file_path)

    if file_path.startswith("http://") or file_path.startswith("https://"):
        parsed = urlparse(file_path)
        file_path = parsed.path

    while file_path.startswith("//"):
        file_path = file_path[1:]

    if not file_path.startswith("/"):
        file_path = "/" + file_path

    return file_path

@app.get("/nas/preview-stream")
async def preview_file_stream(file_path: str = Query(...)):
    try:
        normalized_path = normalize_nas_file_path(file_path)
        filename = normalized_path.split("/")[-1]

        client, response = await get_synology_stream_client(normalized_path)

        async def file_iterator():
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
            finally:
                await response.aclose()
                await client.aclose()

        return StreamingResponse(
            file_iterator(),
            media_type=get_media_type(filename),
            headers={
                "Content-Disposition": f'inline; filename="{filename}"'
            },
        )

    except HTTPException:
        raise

    except Exception as e:
        await clear_synology_sid()
        raise HTTPException(
            status_code=500,
            detail=f"Preview stream failed: {str(e)}",
        )

@app.get("/nas/download")
async def download_file(file_path: str = Query(...)):
    sid = await get_synology_sid()
    filename = file_path.split("/")[-1]

    async def file_iterator():
        async with httpx.AsyncClient(verify=False, timeout=None) as client:
            async with client.stream(
                "GET",
                f"{SYNOLOGY_BASE_URL}/webapi/entry.cgi",
                params={
                    "api": "SYNO.FileStation.Download",
                    "version": "2",
                    "method": "download",
                    "path": file_path,
                    "mode": "download",
                    "_sid": sid,
                },
            ) as response:

                if response.status_code != 200:
                    await clear_synology_sid()
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to download file from NAS",
                    )

                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(
        file_iterator(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )