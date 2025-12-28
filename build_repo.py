import os
import tarfile
import gzip
import shutil

import os, sys, tarfile, gzip, shutil

# Lấy thư mục gốc (py hoặc exe)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)  # fix working dir

# 🔑 Khai báo trước
DEBS_DIR = os.path.join(BASE_DIR, "debs")
PACKAGES_FILE = os.path.join(BASE_DIR, "Packages")
PACKAGES_GZ = os.path.join(BASE_DIR, "Packages.gz")
RELEASE_FILE = os.path.join(BASE_DIR, "Release")
INDEX_FILE = os.path.join(BASE_DIR, "index.html")

# ✅ Debug in ra sau khi khai báo
print("🔍 Đang tìm thư mục debs tại:", DEBS_DIR)
if os.path.exists(DEBS_DIR):
    print("📂 Nội dung thư mục debs:", os.listdir(DEBS_DIR))
else:
    print("⚠ Không tìm thấy thư mục debs")


DEBS_DIR = os.path.join(BASE_DIR, "debs")
PACKAGES_FILE = os.path.join(BASE_DIR, "Packages")
PACKAGES_GZ = os.path.join(BASE_DIR, "Packages.gz")
RELEASE_FILE = os.path.join(BASE_DIR, "Release")
INDEX_FILE = os.path.join(BASE_DIR, "index.html")

REQUIRED_FIELDS = ["Package", "Name", "Version", "Architecture", "Description"]

def extract_control_from_deb(deb_path):
    """Trích dữ liệu control từ .deb"""
    with open(deb_path, "rb") as f:
        data = f.read()

    if not data.startswith(b"!<arch>\n"):
        return ""

    offset = 8
    control_data = ""
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

def ensure_required_fields(control_data, deb_file):
    """Đảm bảo control có đủ field, nếu thiếu thì thêm giá trị mặc định"""
    lines = control_data.strip().splitlines()
    fields = {line.split(":")[0].strip(): line.split(":", 1)[1].strip() for line in lines if ":" in line}

    added = []
    for field in REQUIRED_FIELDS:
        if field not in fields:
            if field == "Package":
                fields[field] = os.path.splitext(deb_file)[0]
            elif field == "Name":
                fields[field] = os.path.splitext(deb_file)[0]
            elif field == "Version":
                fields[field] = "1.0"
            elif field == "Architecture":
                fields[field] = "iphoneos-arm64"
            elif field == "Description":
                fields[field] = "No description"
            added.append(field)

    if added:
        print(f"⚠ Gói {deb_file} thiếu {', '.join(added)} → đã tự thêm.")

    return "\n".join(f"{k}: {v}" for k, v in fields.items())

def duplicate_deb_for_arm64():
    """Nhân bản file .deb iphoneos-arm -> iphoneos-arm64"""
    for file in os.listdir(DEBS_DIR):
        if file.endswith("_iphoneos-arm.deb"):
            src = os.path.join(DEBS_DIR, file)
            dst = os.path.join(DEBS_DIR, file.replace("iphoneos-arm", "iphoneos-arm64"))
            if not os.path.exists(dst):
                shutil.copy(src, dst)
                print(f"📑 Đã nhân bản {file} → {os.path.basename(dst)}")

def build_packages():
    print("🔨 Building Packages list...")
    entries = []
    tweak_names = []
    for file in os.listdir(DEBS_DIR):
        if file.endswith(".deb"):
            deb_path = os.path.join(DEBS_DIR, file)
            size = os.path.getsize(deb_path)
            control_data = extract_control_from_deb(deb_path)

            if not control_data:
                print(f"⚠ Không đọc được control trong {file}")
                continue

            control_data = ensure_required_fields(control_data, file)

            # Lấy Name từ control để đưa vào index.html
            for line in control_data.splitlines():
                if line.startswith("Name:"):
                    tweak_names.append(line.split(":",1)[1].strip())

            print(f"\n📦 Control info của {file}:\n{control_data}\n")

            entry = control_data.strip() + f"\nFilename: debs/{file}\nSize: {size}\n\n"
            entries.append(entry)

    if not entries:
        print("⚠ Không tìm thấy gói .deb nào trong debs/")
        return []

    with open(PACKAGES_FILE, "w", encoding="utf-8") as f:
        f.writelines(entries)

    with open(PACKAGES_FILE, "rb") as f_in, gzip.open(PACKAGES_GZ, "wb") as f_out:
        f_out.writelines(f_in)

    print(f"✅ Done! Packages & Packages.gz đã tạo tại {BASE_DIR}\\")
    return tweak_names

def build_release():
    release_content = """Origin: PHUONGIOSVIET Repo
Label: PHUONGIOSVIET Repo
Suite: stable
Version: 1.0
Codename: ios
Architectures: iphoneos-arm iphoneos-arm64
Components: main
Description: Repo chính thức của PHUONGIOSVIET
Icon: https://phuongiosviet.github.io/iosviet/CydiaIcon.png
"""
    with open(RELEASE_FILE, "w", encoding="utf-8") as f:
        f.write(release_content)
    print("✅ File Release đã được tạo/cập nhật")

def update_index_with_tweaks(tweaks):
    if not os.path.exists(INDEX_FILE):
        print("⚠ Không tìm thấy index.html để update.")
        return

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    start = html.find("<ul class=\"tweaks\">")
    end = html.find("</ul>", start)
    if start == -1 or end == -1:
        print("⚠ index.html không có block <ul class=\"tweaks\">.")
        return

    new_list = "<ul class=\"tweaks\">\n"
    for tweak in tweaks:
        new_list += f"  <li>{tweak}</li>\n"
    new_list += "</ul>"

    new_html = html[:start] + new_list + html[end+5:]

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(new_html)

    print("✅ index.html đã update danh sách tweaks.")

if __name__ == "__main__":
    if not os.path.exists(DEBS_DIR):
        print("⚠ Thư mục debs\\ không tồn tại trong repo!")
    else:
        duplicate_deb_for_arm64()
        tweak_list = build_packages()
        build_release()
        if tweak_list:
            update_index_with_tweaks(tweak_list)
