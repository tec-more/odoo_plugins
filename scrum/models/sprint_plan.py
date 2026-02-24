# -*- coding: utf-8 -*-
from odoo import models, fields, api,_

class ScrumSprintPlan(models.Model):
    _name = 'scrum.sprint_plan'
    _description = 'Scrum Sprint Plan'
    _order = 'start_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    project_id = fields.Many2one('project.project', string='Project', required=True)
    team_id = fields.Many2one('scrum.team', string='Team', domain="[('project_id', '=', project_id)]", store=True, required=True)
    iteration_number = fields.Integer(string='Iteration Number', default=0)

    @api.depends('project_id', 'team_id', 'iteration_number')
    def _compute_name(self):
        for record in self:
            if record.project_id and record.team_id and record.iteration_number:
                record.name = f"{record.project_id.name}-{record.team_id.name}-迭代{record.iteration_number}"
            else:
                record.name = False

    @api.model
    def create(self, vals):
        if not vals.get('iteration_number'):
            project_id = vals.get('project_id')
            team_id = vals.get('team_id')
            if project_id and team_id:
                max_iteration = self.search([
                    ('project_id', '=', project_id),
                    ('team_id', '=', team_id)
                ], order='iteration_number desc', limit=1).iteration_number
                vals['iteration_number'] = (max_iteration or 0) + 1
        return super().create(vals)
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

