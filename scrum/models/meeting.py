# -*- coding: utf-8 -*-
from odoo import models, fields, api,_

class ScrumDailyMeeting(models.Model):
    _name = 'scrum.daily_meeting'
    _description = 'Scrum Daily Meeting'
    _order = 'meeting_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    sprint_plan_id = fields.Many2one('scrum.sprint_plan', string='Sprint Plan', required=True)
    meeting_date = fields.Date(string='Meeting Date', required=True, default=fields.Date.today)
    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')
    discussion_points = fields.Text(string='Discussion Points')
    impediments = fields.Text(string='Impediments')
    notes = fields.Text(string='Notes')
    status = fields.Selection([
        ('planned', _('Planned')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ], string='Status', default='planned', tracking=True)
    attendance_count = fields.Integer(string='Attendance Count', default=0)

    @api.onchange('sprint_plan_id')
    def _onchange_sprint_plan_id(self):
        if self.sprint_plan_id:
            self.project_id = self.sprint_plan_id.project_id

    project_id = fields.Many2one('project.project', string='Project', related='sprint_plan_id.project_id', store=True, readonly=True)
    team_id = fields.Many2one('scrum.team', related='sprint_plan_id.team_id', string='Team', store=True, required=True)
    team_member_ids = fields.Many2many('scrum.team_member', string='Team Members', domain="[('team_id', '=', team_id)]")
    
    def action_start(self):
        self.ensure_one()
        self.write({'status': 'in_progress'})
    
    def action_complete(self):
        self.ensure_one()
        self.write({'status': 'completed'})
class ScrumSprintReviewMeeting(models.Model):
    _name = 'scrum.sprint_review_meeting'
    _description = 'Scrum Sprint Review Meeting'
    _order = 'meeting_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    sprint_plan_id = fields.Many2one('scrum.sprint_plan', string='Sprint Plan', required=True)
    meeting_date = fields.Date(string='Meeting Date', required=True, default=fields.Date.today)
    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')
    demo_items = fields.Text(string='Demo Items')
    feedback = fields.Text(string='Feedback')
    action_items = fields.Text(string='Action Items')
    notes = fields.Text(string='Notes')
    status = fields.Selection([
        ('planned', _('Planned')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ], string='Status', default='planned', tracking=True)
    attendance_count = fields.Integer(string='Attendance Count', default=0)

    @api.onchange('sprint_plan_id')
    def _onchange_sprint_plan_id(self):
        if self.sprint_plan_id:
            self.project_id = self.sprint_plan_id.project_id

    project_id = fields.Many2one('project.project', string='Project', related='sprint_plan_id.project_id', store=True, readonly=True)
    team_id = fields.Many2one('scrum.team', related='sprint_plan_id.team_id', string='Team', store=True, required=True)
    team_member_ids = fields.Many2many('scrum.team_member', string='Team Members', domain="[('team_id', '=', team_id)]")
    
    def action_start(self):
        self.ensure_one()
        self.write({'status': 'in_progress'})
    
    def action_complete(self):
        self.ensure_one()
        self.write({'status': 'completed'})
class ScrumIterationReviewMeeting(models.Model):
    _name = 'scrum.iteration_review_meeting'
    _description = 'Scrum Iteration Review Meeting'
    _order = 'meeting_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    sprint_plan_id = fields.Many2one('scrum.sprint_plan', string='Sprint Plan', required=True)
    meeting_date = fields.Date(string='Meeting Date', required=True, default=fields.Date.today)
    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')
    retrospective_points = fields.Text(string='Retrospective Points')
    improvements = fields.Text(string='Improvements')
    action_items = fields.Text(string='Action Items')
    notes = fields.Text(string='Notes')
    status = fields.Selection([
        ('planned', _('Planned')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ], string='Status', default='planned', tracking=True)
    attendance_count = fields.Integer(string='Attendance Count', default=0)

    @api.onchange('sprint_plan_id')
    def _onchange_sprint_plan_id(self):
        if self.sprint_plan_id:
            self.project_id = self.sprint_plan_id.project_id

    project_id = fields.Many2one('project.project', string='Project', related='sprint_plan_id.project_id', store=True, readonly=True)
    team_id = fields.Many2one('scrum.team', related='sprint_plan_id.team_id', string='Team', store=True, required=True)
    team_member_ids = fields.Many2many('scrum.team_member', string='Team Members', domain="[('team_id', '=', team_id)]")
    
    def action_start(self):
        self.ensure_one()
        self.write({'status': 'in_progress'})
    
    def action_complete(self):
        self.ensure_one()
        self.write({'status': 'completed'})