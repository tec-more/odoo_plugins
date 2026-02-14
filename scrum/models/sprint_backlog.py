# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ScrumSprintBacklog(models.Model):
    _name = 'scrum.sprint_backlog'
    _description = 'Scrum Sprint Backlog'
    _order = 'start_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    sprint_plan_id = fields.Many2one('scrum.sprint_plan', string='Sprint Plan', required=True)
    # product_backlog_id = fields.Many2one('scrum.product_backlog', string='Product Backlog', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    status = fields.Selection([
        ('planning', _('Planning')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ], string='Status', default='planning')
    goal = fields.Text(string='Sprint Goal')
    user_story_id = fields.Many2one('scrum.user_story', string='User Stories', required=True)
    sprint_task_ids = fields.One2many('scrum.sprint_task', 'sprint_backlog_id', string='Sprint Tasks')
    # daily_meeting_ids = fields.One2many('scrum.daily_meeting', 'sprint_backlog_id', string='Daily Meetings')

    @api.depends('user_story_id')
    def _compute_total_story_points(self):
        for record in self:
            record.total_story_points = record.user_story_id.estimated_story_points if record.user_story_id else 0

    total_story_points = fields.Float(string='Total Story Points', compute='_compute_total_story_points', store=True)

    @api.depends('sprint_task_ids')
    def _compute_completed_tasks(self):
        for record in self:
            completed_tasks = sum(1 for task in record.sprint_task_ids if task.status == 'done')
            total_tasks = len(record.sprint_task_ids)
            record.completed_tasks = completed_tasks
            record.total_tasks = total_tasks
            record.completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    completed_tasks = fields.Integer(string='Completed Tasks', compute='_compute_completed_tasks', store=True)
    total_tasks = fields.Integer(string='Total Tasks', compute='_compute_completed_tasks', store=True)
    completion_percentage = fields.Float(string='Completion Percentage', compute='_compute_completed_tasks', store=True)

    @api.onchange('sprint_plan_id')
    def _onchange_sprint_plan_id(self):
        if self.sprint_plan_id:
            self.project_id = self.sprint_plan_id.project_id

    project_id = fields.Many2one('project.project', string='Project', related='sprint_plan_id.project_id', store=True, readonly=True)
