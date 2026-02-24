# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ProjectProjectInherit(models.Model):
    _inherit = 'project.project'

    team_ids = fields.One2many('scrum.team', 'project_id', string='Scrum Teams')
    scrum_status = fields.Selection([
        ('draft', _('Draft')),
        ('active', _('Active')),
        ('on_hold', _('On Hold')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ], string='Scrum Status', default='draft', tracking=True)
    
    @api.depends('team_ids', 'team_ids.sprint_plan_ids')
    def _compute_sprint_count(self):
        for record in self:
            record.sprint_count = sum(len(team.sprint_plan_ids) for team in record.team_ids)
    
    @api.depends('team_ids', 'team_ids.team_member_ids')
    def _compute_team_member_count(self):
        for record in self:
            record.team_member_count = sum(len(team.team_member_ids) for team in record.team_ids)
    
    @api.depends('team_ids', 'team_ids.sprint_plan_ids', 'team_ids.sprint_plan_ids.status')
    def _compute_active_sprint_count(self):
        for record in self:
            record.active_sprint_count = sum(
                1 for team in record.team_ids
                for sprint in team.sprint_plan_ids
                if sprint.status == 'in_progress'
            )
    
    sprint_count = fields.Integer(string='Sprint Count', compute='_compute_sprint_count', store=True)
    team_member_count = fields.Integer(string='Team Member Count', compute='_compute_team_member_count', store=True)
    active_sprint_count = fields.Integer(string='Active Sprint Count', compute='_compute_active_sprint_count', store=True)
