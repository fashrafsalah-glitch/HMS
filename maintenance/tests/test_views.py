# اختبارات الـ Views للـ CMMS
# هنا بنختبر جميع الصفحات والـ Views والاستجابات

from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from maintenance.models import Device
from maintenance.models_cmms import ServiceRequest, WorkOrder, JobPlan
from maintenance.models_spare_parts import Supplier, SparePart
from maintenance.permissions import setup_cmms_permissions


class CMMSViewsTestCase(TestCase):
    """الفئة الأساسية لاختبارات Views"""
    
    def setUp(self):
        """إعداد البيانات المشتركة للاختبارات"""
        # إنشاء المستخدمين
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True
        )
        
        self.technician_user = User.objects.create_user(
            username='technician',
            email='tech@example.com',
            password='testpass123'
        )
        
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='testpass123'
        )
        
        # إعداد الصلاحيات
        setup_cmms_permissions()
        
        # إضافة المستخدمين للمجموعات
        admin_group = Group.objects.get(name='CMMS_Admin')
        technician_group = Group.objects.get(name='CMMS_Technician')
        
        self.admin_user.groups.add(admin_group)
        self.technician_user.groups.add(technician_group)
        
        # إنشاء البيانات الأساسية
        self.device = Device.objects.create(
            name='جهاز اختبار',
            serial_number='TEST001',
            category='medical',
            status='operational'
        )
        
        self.supplier = Supplier.objects.create(
            name='مورد اختبار',
            contact_person='أحمد محمد',
            email='supplier@example.com'
        )
        
        self.spare_part = SparePart.objects.create(
            name='قطعة اختبار',
            part_number='PART001',
            supplier=self.supplier,
            cost=Decimal('100.00'),
            quantity=10
        )
        
        self.client = Client()


class ServiceRequestViewsTest(CMMSViewsTestCase):
    """اختبارات صفحات طلبات الخدمة"""
    
    def test_service_request_list_view(self):
        """اختبار صفحة قائمة طلبات الخدمة"""
        # تسجيل الدخول كمدير
        self.client.login(username='admin', password='testpass123')
        
        # إنشاء طلب خدمة للاختبار
        ServiceRequest.objects.create(
            title='طلب اختبار',
            description='وصف الطلب',
            device=self.device,
            requested_by=self.admin_user
        )
        
        response = self.client.get(reverse('maintenance:service_request_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'طلب اختبار')
        self.assertContains(response, 'جهاز اختبار')
        
    def test_service_request_create_view(self):
        """اختبار صفحة إنشاء طلب خدمة"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('maintenance:service_request_create'))
        self.assertEqual(response.status_code, 200)
        
        # اختبار إنشاء طلب جديد
        data = {
            'title': 'طلب جديد',
            'description': 'وصف الطلب الجديد',
            'device': self.device.id,
            'priority': 'medium',
            'request_type': 'breakdown'
        }
        
        response = self.client.post(reverse('maintenance:service_request_create'), data)
        self.assertEqual(response.status_code, 302)  # إعادة توجيه بعد النجاح
        
        # التحقق من إنشاء الطلب
        self.assertTrue(
            ServiceRequest.objects.filter(title='طلب جديد').exists()
        )
        
    def test_service_request_detail_view(self):
        """اختبار صفحة تفاصيل طلب الخدمة"""
        self.client.login(username='admin', password='testpass123')
        
        service_request = ServiceRequest.objects.create(
            title='طلب اختبار',
            description='وصف الطلب',
            device=self.device,
            requested_by=self.admin_user
        )
        
        response = self.client.get(
            reverse('maintenance:service_request_detail', args=[service_request.id])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'طلب اختبار')
        self.assertContains(response, service_request.description)
        
    def test_service_request_unauthorized_access(self):
        """اختبار منع الوصول غير المصرح به"""
        # محاولة الوصول بدون تسجيل دخول
        response = self.client.get(reverse('maintenance:service_request_list'))
        self.assertEqual(response.status_code, 302)  # إعادة توجيه لصفحة تسجيل الدخول
        
        # تسجيل دخول مستخدم عادي بدون صلاحيات
        self.client.login(username='user', password='testpass123')
        response = self.client.get(reverse('maintenance:service_request_create'))
        self.assertEqual(response.status_code, 403)  # ممنوع


class WorkOrderViewsTest(CMMSViewsTestCase):
    """اختبارات صفحات أوامر الشغل"""
    
    def setUp(self):
        super().setUp()
        
        self.service_request = ServiceRequest.objects.create(
            title='طلب اختبار',
            description='وصف الطلب',
            device=self.device,
            requested_by=self.admin_user
        )
        
        self.job_plan = JobPlan.objects.create(
            name='خطة عمل اختبار',
            description='وصف خطة العمل',
            instructions='تعليمات التنفيذ',
            estimated_duration=120,
            created_by=self.admin_user
        )
        
    def test_work_order_list_view(self):
        """اختبار صفحة قائمة أوامر الشغل"""
        self.client.login(username='admin', password='testpass123')
        
        WorkOrder.objects.create(
            service_request=self.service_request,
            assigned_technician=self.technician_user,
            job_plan=self.job_plan
        )
        
        response = self.client.get(reverse('maintenance:work_order_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'طلب اختبار')
        
    def test_work_order_create_view(self):
        """اختبار صفحة إنشاء أمر شغل"""
        self.client.login(username='admin', password='testpass123')
        
        data = {
            'service_request': self.service_request.id,
            'assigned_technician': self.technician_user.id,
            'job_plan': self.job_plan.id
        }
        
        response = self.client.post(reverse('maintenance:work_order_create'), data)
        self.assertEqual(response.status_code, 302)
        
        # التحقق من إنشاء أمر الشغل
        self.assertTrue(
            WorkOrder.objects.filter(service_request=self.service_request).exists()
        )
        
    def test_work_order_update_status(self):
        """اختبار تحديث حالة أمر الشغل"""
        self.client.login(username='technician', password='testpass123')
        
        work_order = WorkOrder.objects.create(
            service_request=self.service_request,
            assigned_technician=self.technician_user,
            job_plan=self.job_plan
        )
        
        data = {
            'status': 'in_progress',
            'work_performed': 'بدء العمل',
            'start_time': timezone.now().isoformat()
        }
        
        response = self.client.post(
            reverse('maintenance:work_order_update', args=[work_order.id]),
            data
        )
        
        self.assertEqual(response.status_code, 302)
        
        work_order.refresh_from_db()
        self.assertEqual(work_order.status, 'in_progress')


class DashboardViewsTest(CMMSViewsTestCase):
    """اختبارات صفحات لوحة التحكم"""
    
    def test_cmms_dashboard_view(self):
        """اختبار صفحة لوحة تحكم CMMS"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('maintenance:cmms_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'لوحة تحكم CMMS')
        
    def test_dashboard_api_data(self):
        """اختبار API بيانات لوحة التحكم"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('maintenance:dashboard_api_data'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # التحقق من وجود البيانات المطلوبة
        data = response.json()
        self.assertIn('total_devices', data)
        self.assertIn('active_work_orders', data)
        self.assertIn('pending_service_requests', data)


class SparePartsViewsTest(CMMSViewsTestCase):
    """اختبارات صفحات قطع الغيار"""
    
    def test_spare_parts_list_view(self):
        """اختبار صفحة قائمة قطع الغيار"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('maintenance:spare_part_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'قطعة اختبار')
        self.assertContains(response, 'PART001')
        
    def test_spare_part_detail_view(self):
        """اختبار صفحة تفاصيل قطعة الغيار"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(
            reverse('maintenance:spare_part_detail', args=[self.spare_part.id])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'قطعة اختبار')
        self.assertContains(response, 'PART001')
        self.assertContains(response, '100.00')
        
    def test_spare_part_create_view(self):
        """اختبار صفحة إنشاء قطعة غيار"""
        self.client.login(username='admin', password='testpass123')
        
        data = {
            'name': 'قطعة جديدة',
            'part_number': 'PART002',
            'supplier': self.supplier.id,
            'cost': '150.00',
            'quantity': 5,
            'minimum_stock': 2,
            'unit': 'قطعة'
        }
        
        response = self.client.post(reverse('maintenance:spare_part_create'), data)
        self.assertEqual(response.status_code, 302)
        
        # التحقق من إنشاء القطعة
        self.assertTrue(
            SparePart.objects.filter(name='قطعة جديدة').exists()
        )


class PermissionsTest(CMMSViewsTestCase):
    """اختبارات الصلاحيات والأمان"""
    
    def test_admin_permissions(self):
        """اختبار صلاحيات المدير"""
        self.client.login(username='admin', password='testpass123')
        
        # يجب أن يتمكن المدير من الوصول لجميع الصفحات
        urls = [
            'maintenance:service_request_list',
            'maintenance:work_order_list',
            'maintenance:spare_part_list',
            'maintenance:cmms_dashboard'
        ]
        
        for url_name in urls:
            response = self.client.get(reverse(url_name))
            self.assertIn(response.status_code, [200, 302])
            
    def test_technician_permissions(self):
        """اختبار صلاحيات الفني"""
        self.client.login(username='technician', password='testpass123')
        
        # يجب أن يتمكن الفني من عرض أوامر الشغل المعينة له
        response = self.client.get(reverse('maintenance:work_order_list'))
        self.assertEqual(response.status_code, 200)
        
        # لكن لا يجب أن يتمكن من إنشاء طلبات خدمة جديدة
        response = self.client.get(reverse('maintenance:service_request_create'))
        self.assertEqual(response.status_code, 403)
        
    def test_regular_user_permissions(self):
        """اختبار صلاحيات المستخدم العادي"""
        self.client.login(username='user', password='testpass123')
        
        # المستخدم العادي لا يجب أن يتمكن من الوصول لصفحات CMMS
        restricted_urls = [
            'maintenance:work_order_list',
            'maintenance:spare_part_create',
            'maintenance:cmms_dashboard'
        ]
        
        for url_name in restricted_urls:
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 403)


class SearchAndFilterTest(CMMSViewsTestCase):
    """اختبارات البحث والتصفية"""
    
    def setUp(self):
        super().setUp()
        
        # إنشاء بيانات إضافية للاختبار
        self.device2 = Device.objects.create(
            name='جهاز آخر',
            serial_number='TEST002',
            category='laboratory'
        )
        
        ServiceRequest.objects.create(
            title='طلب عاجل',
            description='طلب عاجل للإصلاح',
            device=self.device,
            requested_by=self.admin_user,
            priority='high',
            status='new'
        )
        
        ServiceRequest.objects.create(
            title='طلب عادي',
            description='طلب عادي للصيانة',
            device=self.device2,
            requested_by=self.admin_user,
            priority='medium',
            status='assigned'
        )
        
    def test_service_request_search(self):
        """اختبار البحث في طلبات الخدمة"""
        self.client.login(username='admin', password='testpass123')
        
        # البحث بالعنوان
        response = self.client.get(
            reverse('maintenance:service_request_list') + '?search=عاجل'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'طلب عاجل')
        self.assertNotContains(response, 'طلب عادي')
        
    def test_service_request_filter_by_status(self):
        """اختبار التصفية حسب الحالة"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(
            reverse('maintenance:service_request_list') + '?status=new'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'طلب عاجل')
        self.assertNotContains(response, 'طلب عادي')
        
    def test_service_request_filter_by_priority(self):
        """اختبار التصفية حسب الأولوية"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(
            reverse('maintenance:service_request_list') + '?priority=high'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'طلب عاجل')
        self.assertNotContains(response, 'طلب عادي')


class AjaxViewsTest(CMMSViewsTestCase):
    """اختبارات طلبات AJAX"""
    
    def test_device_autocomplete(self):
        """اختبار الإكمال التلقائي للأجهزة"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(
            reverse('maintenance:device_autocomplete') + '?q=اختبار'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) > 0)
        
    def test_work_order_status_update_ajax(self):
        """اختبار تحديث حالة أمر الشغل عبر AJAX"""
        self.client.login(username='technician', password='testpass123')
        
        service_request = ServiceRequest.objects.create(
            title='طلب اختبار',
            description='وصف الطلب',
            device=self.device,
            requested_by=self.admin_user
        )
        
        work_order = WorkOrder.objects.create(
            service_request=service_request,
            assigned_technician=self.technician_user
        )
        
        data = {
            'status': 'in_progress',
            'work_performed': 'بدء العمل'
        }
        
        response = self.client.post(
            reverse('maintenance:work_order_update_status', args=[work_order.id]),
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        work_order.refresh_from_db()
        self.assertEqual(work_order.status, 'in_progress')


class FormValidationTest(CMMSViewsTestCase):
    """اختبارات التحقق من صحة النماذج"""
    
    def test_service_request_form_validation(self):
        """اختبار التحقق من نموذج طلب الخدمة"""
        self.client.login(username='admin', password='testpass123')
        
        # بيانات ناقصة
        data = {
            'title': '',  # عنوان فارغ
            'description': 'وصف الطلب',
            'device': self.device.id
        }
        
        response = self.client.post(reverse('maintenance:service_request_create'), data)
        
        # يجب أن يعود للنموذج مع أخطاء
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'هذا الحقل مطلوب')
        
    def test_spare_part_form_validation(self):
        """اختبار التحقق من نموذج قطعة الغيار"""
        self.client.login(username='admin', password='testpass123')
        
        # رقم قطعة مكرر
        data = {
            'name': 'قطعة جديدة',
            'part_number': 'PART001',  # رقم موجود مسبقاً
            'supplier': self.supplier.id,
            'cost': '150.00',
            'quantity': 5
        }
        
        response = self.client.post(reverse('maintenance:spare_part_create'), data)
        
        # يجب أن يعود للنموذج مع خطأ
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'رقم القطعة موجود مسبقاً')
