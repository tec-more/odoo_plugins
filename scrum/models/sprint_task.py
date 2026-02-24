# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api,_

class ScrumSprintTask(models.Model):
    _name = 'scrum.sprint_task'
    _description = 'Scrum Sprint Task'
    _order = 'priority desc, create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _default_sprint_stage(self):
        stage = self.env['scrum.sprint_stage'].search([], order='sequence asc', limit=1)
        return stage.id if stage else False

    name = fields.Char(string='Name', required=True)
    sprint_backlog_id = fields.Many2one('scrum.sprint_backlog', string='Sprint Backlog', required=True)
    user_story_id = fields.Many2one('scrum.user_story', string='User Story')
    description = fields.Text(string='Description')
    priority = fields.Integer(string='Priority', default=1)
    sprint_stage_id = fields.Many2one('scrum.sprint_stage', string='Sprint Stage', required=True, default=lambda self: self._default_sprint_stage(), group_expand='_read_group_expand_full')
    team_id = fields.Many2one('scrum.team', related='sprint_backlog_id.sprint_plan_id.team_id', string='Team', store=True)
    assigned_to = fields.Many2one('scrum.team_member', string='Assigned To', domain="[('team_id', '=', team_id)]")
    
    estimated_hours = fields.Float(string='Estimated Hours')
    actual_hours = fields.Float(string='Actual Hours')
    
    @api.onchange('sprint_stage_id')
    def _onchange_sprint_stage_id(self):
        if self.sprint_stage_id and self.sprint_stage_id.name.lower() == 'done':
            if not self.actual_hours:
                self.actual_hours = self.estimated_hours

    @api.onchange('sprint_backlog_id')
    def _onchange_sprint_backlog_id(self):
        if self.sprint_backlog_id:
            self.project_id = self.sprint_backlog_id.project_id

    project_id = fields.Many2one('project.project', string='Project', related='sprint_backlog_id.project_id', store=True, readonly=True)
    team_member_ids = fields.Many2many('scrum.team_member', string='Team Members', domain="[('team_id', '=', team_id)]")
    
    def write(self, vals):
        result = super().write(vals)
        if 'sprint_stage_id' in vals:
            for record in self:
                if record.user_story_id and vals['sprint_stage_id'] != record.sprint_stage_id.id:
                    done_stage = self.env['scrum.sprint_stage'].search([('name', '=ilike', 'Done')], limit=1)
                    if done_stage and vals['sprint_stage_id'] == done_stage.id and not record.actual_hours:
                        record.actual_hours = record.estimated_hours
                    
                    if record.sprint_backlog_id and record.sprint_backlog_id.sprint_plan_id:
                        self._update_burndown_data(record.sprint_backlog_id.sprint_plan_id)
        return result
    
    def _update_burndown_data(self, sprint_plan):
        self.ensure_one()
        
        burndown_charts = self.env['scrum.burndown_chart'].search([
            ('sprint_plan_id', '=', sprint_plan.id)
        ])
        
        for chart in burndown_charts:
            try:
                chart._update_daily_progress(sprint_plan)
            except Exception as e:
                pass
