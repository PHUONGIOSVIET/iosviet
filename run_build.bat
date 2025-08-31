@echo off
cd /d %~dp0

echo ===============================
echo 🔨 Đang chạy build_repo.exe ...
echo ===============================
build_repo.exe

echo ===============================
echo 📤 Đang push lên GitHub ...
echo ===============================
git add .
git commit -m "Auto build repo"
git push origin main

echo ===============================
echo ✅ Hoàn tất! Đã build và push.
echo ===============================

pause
