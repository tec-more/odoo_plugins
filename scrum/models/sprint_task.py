# -*- coding: utf-8 -*-
from odoo import models, fields, api,_

class ScrumSprintTask(models.Model):
    _name = 'scrum.sprint_task'
    _description = 'Scrum Sprint Task'
    _order = 'priority desc, create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _default_sprint_stage(self):
        """Get default sprint stage"""
        # Return the first stage (To Do)
        stage = self.env['scrum.sprint_stage'].search([], order='sequence asc', limit=1)
        # If no stage found, create a default 'To Do' stage
        if not stage:
            stage = self.env['scrum.sprint_stage'].create({
                'name': 'To Do',
                'sequence': 10
            })
        return stage

    name = fields.Char(string='Name', required=True)
    sprint_backlog_id = fields.Many2one('scrum.sprint_backlog', string='Sprint Backlog', required=True)
    user_story_id = fields.Many2one('scrum.user_story', string='User Story')
    description = fields.Text(string='Description')
    priority = fields.Integer(string='Priority', default=1)
    sprint_stage_id = fields.Many2one('scrum.sprint_stage', string='Sprint Stage', required=True, default=lambda self: self._default_sprint_stage(),group_expand='_read_group_expand_full')
    assigned_to = fields.Many2one('res.users', string='Assigned To')
    

    estimated_hours = fields.Float(string='Estimated Hours')
    actual_hours = fields.Float(string='Actual Hours')

    @api.onchange('sprint_backlog_id')
    def _onchange_sprint_backlog_id(self):
        if self.sprint_backlog_id:
            self.project_id = self.sprint_backlog_id.project_id

    project_id = fields.Many2one('project.project', string='Project', related='sprint_backlog_id.project_id', store=True, readonly=True)
    team_id = fields.Many2one('scrum.team', related='sprint_backlog_id.sprint_plan_id.team_id', string='Team', store=True, required=True)
    team_member_ids = fields.Many2many('scrum.team_member', string='Team Members', domain="[('team_id', '=', team_id)]")
