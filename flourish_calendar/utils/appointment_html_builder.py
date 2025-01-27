from django.apps import apps as django_apps
from django.template.loader import render_to_string
from edc_appointment.choices import (
    NEW_APPT,
    IN_PROGRESS_APPT,
    INCOMPLETE_APPT,
    COMPLETE_APPT,
    CANCELLED_APPT
)
from edc_appointment.models import Appointment
from edc_base.utils import get_utcnow

from flourish_dashboard.model_wrappers.caregiver_locator_model_wrapper import \
    CaregiverLocatorModelWrapper
from ..choices import APPT_COLOR
from ..model_wrappers import ParticipantNoteModelWrapper
from ..models import AppointmentStatus, ParticipantNote


class AppointmentHtmlBuilder:
    child_appointment_model = 'flourish_child.appointment'
    caregiver_locator_model = 'flourish_caregiver.caregiverlocator'
    child_visit_model = 'flourish_child.childvisit'

    def __init__(self, appointment: Appointment, request) -> None:
        self._appointment = appointment
        self._subject_identifier = self._appointment.subject_identifier
        self.request = request

    @property
    def children_appointment_cls(self):
        return django_apps.get_model('flourish_child.appointment')

    @property
    def caregiver_locator_cls(self):
        return django_apps.get_model(self.caregiver_locator_model)

    @property
    def child_visit_cls(self):
        return django_apps.get_model(self.child_visit_model)

    @property
    def model_obj(self):
        return self._appointment

    @property
    def is_child(self):
        return isinstance(self._appointment, self.children_appointment_cls)

    @property
    def html_wrapped_status(self):
        """
        NEW_APPT,
        IN_PROGRESS_APPT,
        INCOMPLETE_APPT,
        COMPLETE_APPT,
        CANCELLED_APPT⚠️⚠️
        """
        status = self._appointment.appt_status
        if status == NEW_APPT:
            return f'''\
                <span style="color: orange;" title="New Appointment">{self.status} </span>
                '''
        elif status == IN_PROGRESS_APPT:
            return f'''\
                <span style="color: blue;" class="blink-one" title="Inprogress Appointment">{self.status}</span>
                '''
        elif status == COMPLETE_APPT:
            return f'''\
                <span style="color: green;" title="Complete Appointment">{self.status} ✅</span>
                '''
        elif status == INCOMPLETE_APPT:
            return f'''\
                <span style="color: green;" title="Incomplete Appointment">{self.status} ⚠️</span>
                '''
        elif (status == CANCELLED_APPT):
            return f'''\
                <span style="color: red;" title="Cancelled Appointment">{self.status}</span>
                '''

    @property
    def status(self):
        return self._appointment.appt_status.replace("_", " ").title()

    @property
    def status_color(self):

        # ('green', 'red', 'grey', 'yellow')

        status = None

        try:
            appt = AppointmentStatus.objects.get(
                subject_identifier=self.subject_identifier,
                appt_date__date=self._appointment.appt_datetime.date(),
                visit_code = self._appointment.visit_code,)
                    
        except AppointmentStatus.DoesNotExist:
            pass
        else:
            if appt.color == 'green':
                status = 'label-success'
            elif appt.color == 'red':
                status = 'label-danger'
            elif appt.color == 'grey':
                status = 'label-default'
            elif appt.color == 'yellow':
                status = 'label-warning'

        return status

    @property
    def subject_identifier(self):
        return self._subject_identifier

    @property
    def visit_code(self):
        return self._appointment.visit_code

    @property
    def previous_appointments(self):
        # TODO: Change naming
        return self._appointment.history.all()

    @property
    def resceduled_appointments_count(self):
        # TODO: Change naming
        prev_appt = self.previous_appointments.values_list(
            'appt_datetime__date', flat=True)
        prev_appt_set = set(prev_appt)
        return len(prev_appt_set) - 1

    @property
    def last_appointment(self):
        # TODO: Change naming
        appt = self.previous_appointments.exclude(
            timepoint_datetime__date=self._appointment.appt_datetime.date())

        if appt:
            return appt.last().appt_datetime.date()
        else:
            return None

    @property
    def participant_note_wrapper(self):
        participent_note = ParticipantNote()
        return ParticipantNoteModelWrapper(model_obj=participent_note)

    @property
    def appointment_choices(self):
        colors = ('green', 'red', 'yellow')

        color_dictionary = zip(colors, dict(APPT_COLOR).values())

        return color_dictionary

    @property
    def add_reschedule_reason(self):
        # if self.resceduled_appointments_count:
        return f'''<br> <a href='{self.participant_note_wrapper.href}title = {self.subject_identifier} - Reschedule reason'></a> '''

    def _html(self, dashboard_type):
        view_locator_href = None
        status_color = None
        if self.wrapped_locator_obj:
            view_locator_href = self.wrapped_locator_obj.href
        icon = None
        schedule_name = self._appointment.schedule_name
        appt_datetime = self._appointment.appt_datetime
        if (self.is_child and
                '_fu' in schedule_name and 'qt' not in schedule_name):
            try:
                self.child_visit_cls.objects.get(
                    appointment=self._appointment.id)
            except self.child_visit_cls.DoesNotExist:
                cohort_name = schedule_name.split('_')[1]
                icon = f'[{cohort_name.upper()}] ➡️' if appt_datetime >= get_utcnow() else '👩'
                status_color = 'black'
            else:
                icon = '👩'
        elif 'quart' in schedule_name:
            icon = '📞'
        else:
            icon = '👩'
        view = render_to_string('flourish_calendar/appointment_template.html', {
            'status_color': self.status_color or status_color,
            'dashboard_type': dashboard_type,
            'subject_identifier': self.subject_identifier,
            'visit_code': self.visit_code,
            'status': self.status,
            'resceduled_appointments_count': self.resceduled_appointments_count,
            'participant_note_wrapper': self.participant_note_wrapper,
            'icon': icon,
            'appointment_choices': self.appointment_choices,
            'date': self._appointment.appt_datetime.date().isoformat(),
            'is_not_sec': 'sec' not in self._appointment.schedule_name,
            'view_locator_href': view_locator_href
        }, request=self.request)

        return view

    def view_build(self):

        if self.is_child:
            return self._html('child_dashboard')
        else:
            return self._html('subject_dashboard')

    @property
    def locator_obj(self):
        try:
            locator_obj = self.caregiver_locator_cls.objects.get(
                subject_identifier=self.subject_identifier)
        except self.caregiver_locator_cls.DoesNotExist:
            return None
        else:
            return locator_obj

    @property
    def wrapped_locator_obj(self):
        return CaregiverLocatorModelWrapper(self.locator_obj) if self.locator_obj else None
