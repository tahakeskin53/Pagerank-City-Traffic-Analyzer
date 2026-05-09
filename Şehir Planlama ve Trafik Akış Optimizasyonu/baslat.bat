@echo off
chcp 65001 >nul
title PageRank Trafik Analizi — Kurulum ve Baslatma

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║       PageRank Tabanlı Trafik Analizi                ║
echo  ║       San Francisco Yol Ağı Görselleştirmesi         ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: ── Python kontrolü ─────────────────────────────────────────────────────────
echo [1/3] Python kontrol ediliyor...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  HATA: Python bulunamadi!
    echo  Lutfen https://www.python.org/downloads/ adresinden
    echo  Python 3.10 veya ustunu indirip kurun.
    echo  Kurulum sirasinda "Add Python to PATH" secenegini isaretleyin.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  ✓ %PYVER% bulundu.
echo.

:: ── Kütüphane kurulumu ──────────────────────────────────────────────────────
echo [2/3] Gerekli kutuphaneler kuruluyor...
echo  (İlk kurulumda bu adım 3-5 dakika sürebilir)
echo.
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet

if errorlevel 1 (
    echo.
    echo  HATA: Kutuphaneler kurulamadi!
    echo  Internet baglantinizi kontrol edin ve tekrar deneyin.
    echo.
    pause
    exit /b 1
)
echo  ✓ Tum kutuphaneler hazir.
echo.

:: ── Uygulamayı başlat ───────────────────────────────────────────────────────
echo [3/3] Uygulama baslatiliyor...
echo  Tarayici otomatik acilacak: http://localhost:8501
echo  Uygulamayi kapatmak icin bu pencereyi kapatin.
echo.
echo  ════════════════════════════════════════════════════════
echo.

python -m streamlit run app.py --server.headless false

pause
