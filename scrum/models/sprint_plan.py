# -*- coding: utf-8 -*-
from odoo import models, fields, api,_

class ScrumSprintPlan(models.Model):
    _name = 'scrum.sprint_plan'
    _description = 'Scrum Sprint Plan'
    _order = 'start_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    project_id = fields.Many2one('project.project', string='Project', required=True)
    team_id = fields.Many2one('scrum.team', string='Team', domain="[('project_id', '=', project_id)]", store=True, required=True)
    iteration_number = fields.Integer(string='Iteration Number', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    status = fields.Selection([
        ('planning', _('Planning')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ], string='Status', default='planning')
    goal = fields.Text(string='Sprint Goal')
    sprint_backlog_ids = fields.One2many('scrum.sprint_backlog', 'sprint_plan_id', string='Sprint Backlogs')
    daily_meeting_ids = fields.One2many('scrum.daily_meeting', 'sprint_plan_id', string='Daily Meetings')
    sprint_review_meeting_ids = fields.One2many('scrum.sprint_review_meeting', 'sprint_plan_id', string='Sprint Review Meetings')
    iteration_review_meeting_ids = fields.One2many('scrum.iteration_review_meeting', 'sprint_plan_id', string='Iteration Review Meetings')
    team_member_ids = fields.Many2many('scrum.team_member', string='Team Members', domain="[('team_id', '=', team_id)]")

