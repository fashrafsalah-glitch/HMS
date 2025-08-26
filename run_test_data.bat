@echo off
echo Starting CMMS Test Data Generation...
echo.

python manage.py shell -c "exec(open('CMMS_Test_Data_Generator.py').read())"

echo.
echo Test data generation completed!
pause
