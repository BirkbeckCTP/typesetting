from datetime import date, timedelta

from django.db import models
from django.utils import timezone

from plugins.typesetting import plugin_settings
from utils import models as utils_models
from utils import notify_helpers
from events import logic as events_logic


def review_choices():
    return (
        ('accept', 'Accept'),
        ('corrections', 'Corrections Required'),
        ('proofing', 'Proofing Required'),
    )


class TypesettingClaim(models.Model):
    editor = models.ForeignKey('core.Account')
    article = models.OneToOneField('submission.Article')
    claimed = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('editor', 'article',)


class TypesettingRound(models.Model):
    article = models.ForeignKey('submission.Article')
    round_number = models.PositiveIntegerField(default=1)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-round_number', 'date_created')
        unique_together = ('round_number', 'article',)

    def __str__(self):
        return str(self.round_number)

    @property
    def has_completed_proofing(self):
        return GalleyProofing.objects.filter(
            round=self,
            accepted__isnull=False,
            completed__isnull=False,
        )

    @property
    def has_open_tasks(self):
        if hasattr(self, 'typesettingassignment'):
            if not self.typesettingassignment.done:
                return True

        if self.galleyproofing_set.filter(completed__isnull=True).exists():
            return True

        return False

    def close(self, user=None):
        """ Method that closes a round by cancelling any open tasks """
        if hasattr(self, 'typesettingassignment'):
            if self.typesettingassignment.is_active:
                self.typesettingassignment.cancel(user=user)

        for proofing in  self.galleyproofing_set.filter(
            completed__isnull=True,
        ):
            proofing.cancel(user=user)


class TypesettingAssignment(models.Model):
    round = models.OneToOneField(TypesettingRound)
    manager = models.ForeignKey(
        'core.Account',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='manager',
    )
    typesetter = models.ForeignKey(
        'core.Account',
        null=True,
        on_delete=models.SET_NULL,
        related_name='typesetter',
    )

    assigned = models.DateTimeField(default=timezone.now)
    notified = models.BooleanField(default=False)
    accepted = models.DateTimeField(blank=True, null=True)
    due = models.DateField(null=True)
    completed = models.DateTimeField(blank=True, null=True)
    cancelled = models.DateTimeField(blank=True, null=True)
    reviewed = models.BooleanField(default=False)
    review_decision = models.CharField(
        choices=review_choices(),
        max_length=21,
        blank=True,
    )

    task = models.TextField(
        null=True,
        verbose_name='Typesetting Task',
        help_text='Please let the typesetter know what you want them to create'
                  ' and if there are any special circumstances. They will have'
                  ' access to the articles metadata.',
    )
    files_to_typeset = models.ManyToManyField(
        'core.File',
        related_name='files_to_typeset',
        blank=True,
    )
    galleys_created = models.ManyToManyField(
        'core.Galley',
        blank=True,
    )
    typesetter_note = models.TextField(
        blank=True,
        verbose_name='Note to Editor',
    )

    @property
    def time_to_due(self):
        return self.due - timezone.now().date()

    @property
    def is_active(self):
        return self.assigned and not self.completed

    @property
    def status(self):
        if self.cancelled:
            return "cancelled"
        if self.assigned and not self.accepted and not self.completed:
            return "assigned"
        elif self.assigned and self.accepted and not self.completed:
            return "accepted"
        elif self.declined:
            return "declined"
        elif self.done and not self.reviewed:
            return "completed"
        elif self.done and self.reviewed:
            return self.get_review_decision_display()
        else:
            return "unknown"

    @property
    def done(self):
        return self.completed and self.accepted

    @property
    def declined(self):
        return self.completed and not self.accepted

    @property
    def is_overdue(self):
        return self.due and self.due < date.today()

    def reopen(self, user):
        self.completed = self.acccepted = None
        self.notified = False
        utils_models.LogEntry.add_entry(
            types="Typesetting reopened",
            description="The typesetting assignment {self.pk} has been "
            "re-opened by user {user}".format(self=self, user=user),
            level="INFO",
            actor=user,
            target=self.round.article,
        )
        self.save()

    def delete(self, user=None):
        utils_models.LogEntry.add_entry(
            types="Typesetting deleted",
            description="The typesetting assignment {self.pk} has been "
            "deleted by user {user}".format(self=self, user=user),
            level="INFO",
            actor=user,
            target=self.round.article,
        )
        super().delete()

    def cancel(self, user=None):
        utils_models.LogEntry.add_entry(
            types="Typesetting Task cancelled",
            description="The typesetting assignment {self.pk} has been "
            "cancelled by user {user}".format(self=self, user=user),
            level="INFO",
            actor=user,
            target=self.round.article,
        )
        self.cancelled = timezone.now()
        self.save()

    def complete(self, note='', user=None):
        utils_models.LogEntry.add_entry(
            types="Typesetting Task Completed",
            description="The typesetting assignment {self.pk} has been "
                        "completed by user {user}".format(self=self, user=user),
            level="INFO",
            actor=user,
            target=self.round.article,
        )

        self.typesetter_note = note

        self.completed = timezone.now()
        self.save()

    FRIENDLY_STATUSES = {
        "assigned": "Awaiting response from the typesetter.",
        "accepted": "Typesetter has accepted task, awaiting completion.",
        "declined": "Typesetter has declined this task.",
        "completed": "The typesetter has completed their task. "
                     "You should review the uploaded galley files.",
        "cancelled": "The manager has cancelled this typesetting task",
        "closed": "Task closed",
        "unknown": "Task status unknown",
        "Corrections Required": "This article requires corrections.",
        "Proofing Required": "This article requires proofing.",
        "Accept": "Typesetting for this article has been accepted."
    }

    @property
    def friendly_status(self):
        return self.FRIENDLY_STATUSES.get(self.status)


class GalleyProofing(models.Model):
    round = models.ForeignKey(TypesettingRound)
    manager = models.ForeignKey('core.Account', related_name='galley_manager')
    proofreader = models.ForeignKey(
        'core.Account',
        null=True,
        on_delete=models.SET_NULL,

    )
    assigned = models.DateTimeField(default=timezone.now)
    notified = models.BooleanField(default=False)
    due = models.DateTimeField(default=None, verbose_name="Date Due")
    accepted = models.DateTimeField(blank=True, null=True)
    completed = models.DateTimeField(blank=True, null=True)
    cancelled = models.BooleanField(default=False)

    task = models.TextField(
        verbose_name="Proofing Task",
        help_text='If there is any additional information or direction you '
                  'can give the proofreader to complete their task you can '
                  'add it here.',
    )
    proofed_files = models.ManyToManyField('core.Galley', blank=True)
    notes = models.TextField(blank=True)
    annotated_files = models.ManyToManyField('core.File', blank=True)
    
    class Meta:
        ordering = ('assigned', 'accepted', 'pk')

    def __str__(self):
        return 'Proofing for Article {0} by {1}'.format(
            self.round.article.title,
            self.proofreader.full_name(),
        )

    def assign(self, user, skip=False):
        if not skip:
            self.notified = True
            self.save()

        utils_models.LogEntry.add_entry(
            types='Proofreader Assigned',
            description='{} assigned as a proofreader by {}'.format(
                self.proofreader.full_name(),
                user,
            ),
            level='Info',
            actor=user,
            target=self.round.article,
        )

    def cancel(self, user):
        self.cancelled = True
        self.completed = timezone.now()
        self.save()

        utils_models.LogEntry.add_entry(
            types='Proofreading Assignment Cancelled',
            description='Proofing by {} cancelled by {}'.format(
                self.proofreader.full_name(),
                user,
            ),
            level='Info',
            actor=user,
            target=self.round.article,
        )

    def reset(self, user):
        self.cancelled = False
        self.completed = None
        self.accepted = None
        self.save()

        utils_models.LogEntry.add_entry(
            types='Proofreading Assignment Reset',
            description='Proofing by {} reset by {}'.format(
                self.proofreader.full_name(),
                user,
            ),
            level='Info',
            actor=user,
            target=self.round.article,
        )

    def complete(self, user):
        self.cancelled = False
        self.completed = timezone.now()
        self.accepted = timezone.now()
        self.save()

        utils_models.LogEntry.add_entry(
            types='Proofreading Assignment Complete',
            description='Proofing by {} completed'.format(
                user,
            ),
            level='Info',
            actor=user,
            target=self.round.article,
        )

    def unproofed_galleys(self, galleys):
        check = []
        proofed_files = self.proofed_files.all()

        for galley in galleys:
            if galley not in proofed_files:
                check.append(galley)

        return check

    @property
    def time_to_due(self):
        due = self.due - timezone.now()

        if due.days == 0:
            return 'Due Today'
        
        if due < timedelta(0):
            return 'Overdue'

        return '{} days'.format(due.days)

    FRIENDLY_STATUSES = {
        "assigned": "Awaiting response from the proofreader.",
        "accepted": "Proofreader has accepted task, awaiting completion.",
        "declined": "Proofreader has declined this task.",
        "completed": "The proofreader has completed their task. "
                     "You should review their response.",
        "unknown": "Task status unknown.",
        "cancelled": "Task was cancelled by manager/editor."
    }

    @property
    def status(self):
        if self.cancelled:
            return 'cancelled'
        elif self.assigned and self.accepted and not self.completed:
            return 'accepted'
        elif self.assigned and self.completed and not self.accepted:
            return 'declined'
        elif self.assigned and self.completed and self.accepted:
            return 'completed'
        elif self.assigned and not self.accepted and not self.completed:
            return 'assigned'
        else:
            return 'unknown'

    @property
    def friendly_status(self):
        return self.FRIENDLY_STATUSES.get(self.status)
