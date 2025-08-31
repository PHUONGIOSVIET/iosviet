import os
import tarfile
import gzip
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEBS_DIR = os.path.join(BASE_DIR, "debs")
PACKAGES_FILE = os.path.join(DEBS_DIR, "Packages")
PACKAGES_GZ = PACKAGES_FILE + ".gz"

def extract_control_from_deb(deb_path):
    """Trích file control từ .deb"""
    control_data = ""
    with open(deb_path, "rb") as f:
        data = f.read()

    if not data.startswith(b"!<arch>\n"):
        return ""

    offset = 8
    while offset < len(data):
        header = data[offset:offset+60]
        name = header[0:16].decode("utf-8").strip()
        size = int(header[48:58].decode("utf-8").strip())
        file_data = data[offset+60:offset+60+size]

        if size % 2 != 0:
            size += 1
        offset += 60 + size

        if name.startswith("control.tar"):
            tmp_name = os.path.join(BASE_DIR, "tmp_control.tar")
            with open(tmp_name, "wb") as tmpf:
                tmpf.write(file_data)
            try:
                if name.endswith(".gz"):
                    mode = "r:gz"
                elif name.endswith(".xz"):
                    mode = "r:xz"
                elif name.endswith(".bz2"):
                    mode = "r:bz2"
                else:
                    continue
                with tarfile.open(tmp_name, mode) as tarf:
                    for member in tarf.getmembers():
                        if os.path.basename(member.name) == "control":
                            control = tarf.extractfile(member)
                            control_data = control.read().decode("utf-8")
                            break
            finally:
                os.remove(tmp_name)
            break
    return control_data

def build_packages():
    print("🔨 Building Packages list...")
    entries = []
    for file in os.listdir(DEBS_DIR):
        if file.endswith(".deb"):
            deb_path = os.path.join(DEBS_DIR, file)
            control_data = extract_control_from_deb(deb_path)
            if not control_data:
                print(f"⚠ Không đọc được control trong {file}")
                continue
            size = os.path.getsize(deb_path)
            entry = control_data.strip() + f"\nFilename: debs/{file}\nSize: {size}\n\n"
            entries.append(entry)

    with open(PACKAGES_FILE, "w", encoding="utf-8") as f:
        f.writelines(entries)

    with open(PACKAGES_FILE, "rb") as f_in, gzip.open(PACKAGES_GZ, "wb") as f_out:
        f_out.writelines(f_in)

    # copy ra thư mục gốc (sileo-repo\)
    shutil.copy(PACKAGES_FILE, os.path.join(BASE_DIR, "Packages"))
    shutil.copy(PACKAGES_GZ, os.path.join(BASE_DIR, "Packages.gz"))

    print(f"✅ Done! Packages & Packages.gz created in {BASE_DIR}\\")

if __name__ == "__main__":
    if not os.path.exists(DEBS_DIR):
        print("⚠ Thư mục debs\\ không tồn tại!")
    else:
        build_packages()
