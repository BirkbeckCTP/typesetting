from utils import notify_helpers

from plugins.typesetting import models


def send_typesetting_complete(**kwargs):
    request = kwargs['request']
    article = kwargs['article']
    user_content_message = kwargs['user_content_message']
    assignment = kwargs['assignment']

    description = 'Typesetting has been completed for article {0}.'.format(
        article.title)

    log_dict = {
        'level': 'Info', 'action_text': description,
        'types': 'Typesetting Complete',
        'actor': request.user,
        'target': article,
    }

    notify_helpers.send_email_with_body_from_setting_template(
        request, 'typesetting_complete', 'subject_typesetting_complete',
        article.editor_emails(),
        {'article': article},
        log_dict=log_dict,
    )
    notify_helpers.send_slack(request, description, ['slack_editors'])


def send_proofreader_assign_notification(**kwargs):
    pass


def send_proofreader_assign_cancelled(**kwargs):
    pass


def send_proofreader_assign_reset(**kwargs):
    pass


def send_proofreader_assign_complete(**kwargs):
    pass


def send_typesetting_assign_notification(**kwargs):
    pass


def send_typesetting_assign_decision(**kwargs):
    pass


def send_typesetting_assign_complete(**kwargs):
    assignment = kwargs['assignment']
    request = kwargs['request']

    description = 'Typesetting task completed by {0}'.format(
        assignment.typesetter.full_name(),
    )

    log_dict = {
        'level': 'Info',
        'action_text': description,
        'types': 'Typesetting Complete',
        'target': assignment.round.article,
    }

    notify_helpers.send_email_with_body_from_setting_template(
        request,
        'typesetting_typesetter_complete',
        'Typesetting Assignment Complete',
        assignment.manager.email,
        context={'assignment': assignment},
        log_dict=log_dict,
    )
