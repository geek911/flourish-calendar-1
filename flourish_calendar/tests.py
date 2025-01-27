from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.utils import timezone
from django.apps import apps as django_apps

from flourish_calendar.constants import MONTHLY
from flourish_calendar.models import Reminder
from flourish_calendar.utils.reminder_helper import ReminderDuplicator, WorkingDays


class WorkingDaysTests(TestCase):
    def setUp(self):
        self.working_day = WorkingDays()

    def test_holiday(self):
        holiday = django_apps.get_model(self.working_day.holiday_model)(
            local_date=timezone.now().date())
        holiday.save()

        self.assertTrue(self.working_day.holiday(timezone.now().date()))

    def test_is_valid_working_day(self):
        # assuming holidays table is empty
        self.assertTrue(self.working_day.is_valid_working_day(timezone.now().date()))


class ReminderDuplicatorTests(TestCase):
    def setUp(self):
        self.start_date = timezone.now().date()
        self.end_date = self.start_date + relativedelta(months=3)
        self.reminder = Reminder(start_date=self.start_date, end_date=self.end_date,
                                 repeat=MONTHLY, remainder_time=timezone.now().time())
        self.reminder.save()

        self.reminder_duplicator = ReminderDuplicator(self.reminder)

    def test__get_dates_based_on_recurrence(self):
        dates = self.reminder_duplicator._get_dates_based_on_recurrence()
        expected_length = 3
        self.assertEqual(len(dates), expected_length)
        self.assertEqual(dates[0], self.start_date)

    def test__generate_potential_dates(self):
        dates = self.reminder_duplicator._generate_potential_dates()
        expected_dates = [self.start_date + relativedelta(months=month) for month in
                          range(4)]
        self.assertListEqual(dates, expected_dates)

    def test__create_new_reminder(self):
        date = timezone.now().date()
        new_reminder = self.reminder_duplicator._create_new_reminder(date)
        self.assertEqual(new_reminder.datetime.date(), date)

    def test_repeat(self):
        initial_reminders_count = Reminder.objects.count()
        self.reminder_duplicator.repeat()
        final_reminders_count = Reminder.objects.count()
        number_of_created_reminders = final_reminders_count - initial_reminders_count
        self.assertEqual(number_of_created_reminders, 3)
