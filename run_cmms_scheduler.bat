@echo off
REM سكريبت لتشغيل المهام المجدولة للـ CMMS على Windows
REM يمكن إضافته إلى Windows Task Scheduler للتشغيل التلقائي

echo Starting CMMS Scheduler...
echo تشغيل المهام المجدولة للـ CMMS...

REM تغيير المجلد إلى مجلد المشروع
cd /d "e:\JYGKUI\HMS-main"

REM تفعيل البيئة الافتراضية إذا كانت موجودة
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM تشغيل المهام المجدولة
echo Running scheduled tasks...
python manage.py run_cmms_scheduler --verbose

REM فحص حالة الخروج
if %ERRORLEVEL% EQU 0 (
    echo CMMS Scheduler completed successfully!
    echo تم تشغيل المهام بنجاح!
) else (
    echo CMMS Scheduler failed with error code %ERRORLEVEL%
    echo فشل في تشغيل المهام - رمز الخطأ %ERRORLEVEL%
)

REM إيقاف مؤقت لعرض النتائج
pause
