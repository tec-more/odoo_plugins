# -*- coding: utf-8 -*-
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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

    def action_parse_user_story_tasks(self):
        self.ensure_one()
        if not self.user_story_id:
            raise UserError(_('Please assign a User Story first.'))
        
        try:
            content = self.user_story_id.description or ''
            if self.user_story_id.acceptance_criteria:
                content += '\n' + self.user_story_id.acceptance_criteria
            
            tasks_data = self._parse_content_to_tasks(content)
            self._create_sprint_tasks(tasks_data)
            
            self.user_story_id.parsed_tasks_json = json.dumps(tasks_data, ensure_ascii=False, indent=2)
            self.user_story_id.parse_status = 'done'
            
        except Exception as e:
            self.user_story_id.parse_status = 'error'
            self.user_story_id.parse_error = str(e)
            _logger.error('Failed to parse user story to tasks: %s', e)
            raise UserError(_('Failed to parse user story to tasks: %s') % e)

    def _parse_content_to_tasks(self, content):
        tasks = []
        lines = content.split('\n')
        current_task = None
        task_priority = 10
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('#') or line.startswith('- ') or line.startswith('* '):
                if current_task:
                    tasks.append(current_task)
                
                task_name = line.lstrip('#-* ')
                current_task = {
                    'name': task_name,
                    'description': '',
                    'priority': task_priority,
                    'estimated_hours': 0.0,
                }
                task_priority += 10
            elif current_task:
                current_task['description'] += line + '\n'
        
        if current_task:
            tasks.append(current_task)
        
        if not tasks:
            tasks = [{
                'name': 'Task from %s' % self.user_story_id.name,
                'description': content,
                'priority': 10,
                'estimated_hours': 0.0,
            }]
        
        return tasks

    def _create_sprint_tasks(self, tasks_data):
        self.ensure_one()
        sprint_stage = self.env['scrum.sprint_stage'].search([], order='sequence asc', limit=1)
        
        for task_data in tasks_data:
            vals = {
                'name': task_data.get('name', 'Untitled Task'),
                'description': task_data.get('description', ''),
                'user_story_id': self.user_story_id.id,
                'sprint_backlog_id': self.id,
                'priority': task_data.get('priority', 10),
                'estimated_hours': task_data.get('estimated_hours', 0.0),
                'sprint_stage_id': sprint_stage.id if sprint_stage else False,
            }
            self.env['scrum.sprint_task'].create(vals)
