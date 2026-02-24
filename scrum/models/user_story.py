# -*- coding: utf-8 -*-
import base64
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ScrumUserStory(models.Model):
    _name = 'scrum.user_story'
    _description = 'Scrum User Story'
    _order = 'priority desc, create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    product_backlog_id = fields.Many2one('scrum.product_backlog', string='Product Backlog', required=True)
    description = fields.Text(string='Description')
    acceptance_criteria = fields.Text(string='Acceptance Criteria')
    priority = fields.Integer(string='Priority', default=1)
    status = fields.Selection([
        ('to_do', _('To Do')),
        ('in_progress', _('In Progress')),
        ('done', _('Done')),
    ], string='Status', default='to_do')
    estimated_story_points = fields.Float(string='Estimated Story Points')
    team_id = fields.Many2one('scrum.team', string='Team')
    assigned_to = fields.Many2one('scrum.team_member', string='Assigned To', domain="[('team_id', '=', team_id)]")
    sprint_task_ids = fields.One2many('scrum.sprint_task', 'user_story_id', string='Sprint Tasks')
    sprint_backlog_id = fields.Many2one('scrum.sprint_backlog', string='Sprint Backlog')

    parse_status = fields.Selection([
        ('none', _('Not Parsed')),
        ('parsing', _('Parsing')),
        ('done', _('Parsed')),
        ('error', _('Parse Error')),
    ], string='Parse Status', default='none', tracking=True)
    parse_error = fields.Text(string='Parse Error Message')
    parsed_tasks_json = fields.Json(string='Parsed Tasks JSON')
    
    @api.onchange('product_backlog_id')
    def _onchange_product_backlog_id(self):
        if self.product_backlog_id:
            self.project_id = self.product_backlog_id.project_id

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            teams = self.env['scrum.team'].search([('project_id', '=', self.project_id.id)])
            if teams:
                self.team_id = teams[0].id
            else:
                self.team_id = False
        else:
            self.team_id = False
        self.assigned_to = False

    project_id = fields.Many2one('project.project', string='Project', related='product_backlog_id.project_id', store=True, readonly=True)
    
    @api.depends('sprint_task_ids', 'sprint_task_ids.sprint_stage_id')
    def _compute_task_progress(self):
        for record in self:
            tasks = record.sprint_task_ids
            total_tasks = len(tasks)
            if total_tasks == 0:
                record.total_tasks = 0
                record.completed_tasks = 0
                record.task_completion_percentage = 0.0
                continue
            
            done_stage = self.env['scrum.sprint_stage'].search([('name', '=ilike', 'Done')], limit=1)
            if done_stage:
                completed_tasks = sum(1 for task in tasks if task.sprint_stage_id.id == done_stage.id)
            else:
                completed_tasks = 0
            
            record.total_tasks = total_tasks
            record.completed_tasks = completed_tasks
            record.task_completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
    
    @api.depends('status', 'sprint_task_ids', 'sprint_task_ids.sprint_stage_id')
    def _compute_status_display(self):
        for record in self:
            if record.status == 'done':
                record.status_display = 'Done'
            elif record.task_completion_percentage > 0:
                record.status_display = 'In Progress'
            else:
                record.status_display = 'To Do'
    
    total_tasks = fields.Integer(string='Total Tasks', compute='_compute_task_progress', store=True)
    completed_tasks = fields.Integer(string='Completed Tasks', compute='_compute_task_progress', store=True)
    task_completion_percentage = fields.Float(string='Task Completion %', compute='_compute_task_progress', store=True, digits=(5, 2))
    status_display = fields.Char(string='Status Display', compute='_compute_status_display', store=True)
    
    @api.constrains('status')
    def _check_status_consistency(self):
        for record in self:
            if record.status == 'done':
                if record.task_completion_percentage < 100:
                    raise UserError(_('Cannot mark user story as Done. All tasks must be completed first.'))
    
    def write(self, vals):
        result = super().write(vals)
        if 'status' in vals:
            for record in self:
                if record.sprint_backlog_id and vals['status'] != record.status:
                    record._update_sprint_backlog_status()
        return result
    
    def _update_sprint_backlog_status(self):
        self.ensure_one()
        if not self.sprint_backlog_id:
            return
        
        sprint_backlog = self.sprint_backlog_id
        
        if self.status == 'done':
            sprint_backlog.status = 'completed'
        elif self.status == 'in_progress':
            sprint_backlog.status = 'in_progress'

    def action_parse_to_tasks(self):
        self.ensure_one()
        if not self.sprint_backlog_id:
            raise UserError(_('Please assign a Sprint Backlog before parsing tasks.'))
        if not self.sprint_backlog_id.sprint_plan_id:
            raise UserError(_('The Sprint Backlog must be assigned to a Sprint Plan before parsing tasks.'))
        
        self.parse_status = 'parsing'
        self.parse_error = False
        
        try:
            content = self.description or ''
            if self.acceptance_criteria:
                content += '\n' + self.acceptance_criteria
            
            tasks_data = self._parse_content_to_tasks(content)
            
            self.parsed_tasks_json = json.dumps(tasks_data, ensure_ascii=False, indent=2)
            self._create_sprint_tasks(tasks_data)
            
            self.parse_status = 'done'
            
        except Exception as e:
            self.parse_status = 'error'
            self.parse_error = str(e)
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
                'name': 'Task from %s' % self.name,
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
                'user_story_id': self.id,
                'sprint_backlog_id': self.sprint_backlog_id.id,
                'priority': task_data.get('priority', 10),
                'estimated_hours': task_data.get('estimated_hours', 0.0),
                'sprint_stage_id': sprint_stage.id if sprint_stage else False,
            }
            self.env['scrum.sprint_task'].create(vals)

    def action_view_parsed_tasks(self):
        self.ensure_one()
        return {
            'name': _('Parsed Tasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'scrum.sprint_task',
            'view_mode': 'list,form',
            'domain': [('user_story_id', '=', self.id)],
            'context': {'default_user_story_id': self.id, 'default_sprint_backlog_id': self.sprint_backlog_id.id},
        }

    def action_create_sprint_backlog(self):
        self.ensure_one()
        if not self.project_id:
            raise UserError(_('Please assign a Product Backlog with a Project first.'))
        
        return {
            'name': _('Create Sprint Backlog'),
            'type': 'ir.actions.act_window',
            'res_model': 'scrum.sprint_backlog',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': _('Sprint Backlog for %s') % self.name,
                'default_user_story_id': self.id,
                'default_project_id': self.project_id.id,
            },
        }

    def action_create_sprint_plan(self):
        self.ensure_one()
        if not self.project_id:
            raise UserError(_('Please assign a Product Backlog with a Project first.'))
        
        last_sprint = self.env['scrum.sprint_plan'].search([
            ('project_id', '=', self.project_id.id)
        ], order='iteration_number desc', limit=1)
        next_iteration = (last_sprint.iteration_number + 1) if last_sprint else 1
        
        return {
            'name': _('Create Sprint Plan'),
            'type': 'ir.actions.act_window',
            'res_model': 'scrum.sprint_plan',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': _('Sprint %s') % next_iteration,
                'default_project_id': self.project_id.id,
                'default_iteration_number': next_iteration,
            },
        }
    
    def action_analyze_requirements(self):
        self.ensure_one()
        return {
            'name': _('Analyze Requirements'),
            'type': 'ir.actions.act_window',
            'res_model': 'scrum.ai_analysis',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.project_id.id,
                'default_user_story_id': self.id,
                'default_analysis_type': 'requirement',
            },
        }
    
    def action_analyze_quality(self):
        self.ensure_one()
        return {
            'name': _('Analyze Quality'),
            'type': 'ir.actions.act_window',
            'res_model': 'scrum.ai_analysis',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.project_id.id,
                'default_user_story_id': self.id,
                'default_analysis_type': 'quality',
            },
        }
    
    @api.depends('sprint_task_ids')
    def _compute_ai_analysis_count(self):
        for record in self:
            record.ai_analysis_count = self.env['scrum.ai_analysis'].search_count([
                ('user_story_id', '=', record.id)
            ])
    
    ai_analysis_count = fields.Integer(string='AI Analysis Count', compute='_compute_ai_analysis_count')