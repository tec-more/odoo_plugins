# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api,_

_logger = logging.getLogger(__name__)

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
    
    @api.depends('sprint_backlog_ids', 'sprint_backlog_ids.status', 'daily_meeting_ids', 'daily_meeting_ids.status', 'sprint_review_meeting_ids', 'sprint_review_meeting_ids.status', 'iteration_review_meeting_ids', 'iteration_review_meeting_ids.status')
    def _compute_progress_summary(self):
        for record in self:
            sprint_backlogs = record.sprint_backlog_ids
            total_backlogs = len(sprint_backlogs)
            
            if total_backlogs == 0:
                record.completed_backlogs = 0
                record.total_backlogs = 0
                record.backlog_completion_percentage = 0.0
                record.completed_daily_meetings = 0
                record.completed_review_meetings = 0
                record.completed_retrospective_meetings = 0
                continue
            
            completed_backlogs = sum(1 for sb in sprint_backlogs if sb.status == 'completed')
            completed_daily_meetings = sum(1 for dm in record.daily_meeting_ids if dm.status == 'completed')
            completed_review_meetings = sum(1 for rm in record.sprint_review_meeting_ids if rm.status == 'completed')
            completed_retrospective_meetings = sum(1 for im in record.iteration_review_meeting_ids if im.status == 'completed')
            
            record.completed_backlogs = completed_backlogs
            record.total_backlogs = total_backlogs
            record.backlog_completion_percentage = (completed_backlogs / total_backlogs * 100) if total_backlogs > 0 else 0.0
            record.completed_daily_meetings = completed_daily_meetings
            record.completed_review_meetings = completed_review_meetings
            record.completed_retrospective_meetings = completed_retrospective_meetings
    
    @api.constrains('status')
    def _check_status_transition(self):
        for record in self:
            if record.status == 'in_progress':
                if not record.sprint_backlog_ids:
                    raise UserError(_('Cannot start Sprint Plan without any Sprint Backlogs.'))
            elif record.status == 'completed':
                if not any(sb.status == 'completed' for sb in record.sprint_backlog_ids):
                    raise UserError(_('Cannot complete Sprint Plan. At least one Sprint Backlog must be completed.'))
    
    completed_backlogs = fields.Integer(string='Completed Backlogs', compute='_compute_progress_summary', store=True)
    total_backlogs = fields.Integer(string='Total Backlogs', compute='_compute_progress_summary', store=True)
    backlog_completion_percentage = fields.Float(string='Backlog Completion %', compute='_compute_progress_summary', store=True, digits=(5, 2))
    completed_daily_meetings = fields.Integer(string='Completed Daily Meetings', compute='_compute_progress_summary', store=True)
    completed_review_meetings = fields.Integer(string='Completed Review Meetings', compute='_compute_progress_summary', store=True)
    completed_retrospective_meetings = fields.Integer(string='Completed Retrospective Meetings', compute='_compute_progress_summary', store=True)
    
    def action_start(self):
        self.ensure_one()
        if not self.sprint_backlog_ids:
            raise UserError(_('Cannot start Sprint Plan without any Sprint Backlogs.'))
        self.write({'status': 'in_progress'})
    
    def action_complete(self):
        self.ensure_one()
        if not any(sb.status == 'completed' for sb in self.sprint_backlog_ids):
            raise UserError(_('Cannot complete Sprint Plan. At least one Sprint Backlog must be completed.'))
        self.write({'status': 'completed'})
        
        if self.project_id and self.project_id.auto_analyze:
            self._create_auto_ai_analysis()
    
    def _create_auto_ai_analysis(self):
        self.ensure_one()
        try:
            self.env['scrum.ai_analysis'].create({
                'name': f'Auto Analysis - {self.name}',
                'analysis_type': 'sprint_review',
                'project_id': self.project_id.id,
                'sprint_plan_id': self.id,
            }).action_analyze()
        except Exception as e:
            _logger.warning('Auto AI analysis failed for sprint %s: %s', self.name, e)
    
    def action_create_burndown_chart(self):
        self.ensure_one()
        return {
            'name': _('Create Burndown Chart'),
            'type': 'ir.actions.act_window',
            'res_model': 'scrum.burndown_chart',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': f'Burndown Chart - {self.name}',
                'default_sprint_plan_id': self.id,
            },
        }
    
    def action_view_burndown_charts(self):
        self.ensure_one()
        return {
            'name': _('Burndown Charts'),
            'type': 'ir.actions.act_window',
            'res_model': 'scrum.burndown_chart',
            'view_mode': 'tree,form',
            'domain': [('sprint_plan_id', '=', self.id)],
            'context': {'default_sprint_plan_id': self.id},
        }
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
    burndown_chart_ids = fields.One2many('scrum.burndown_chart', 'sprint_plan_id', string='Burndown Charts')
    
    @api.depends('burndown_chart_ids')
    def _compute_has_burndown_chart(self):
        for record in self:
            record.has_burndown_chart = bool(record.burndown_chart_ids)
    
    has_burndown_chart = fields.Boolean(string='Has Burndown Chart', compute='_compute_has_burndown_chart', store=True)

