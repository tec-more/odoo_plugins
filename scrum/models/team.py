# -*- coding: utf-8 -*-
from odoo import models, fields, api , _

class ScrumTeam(models.Model):
    _name = 'scrum.team'
    _description = 'Scrum Agile Team'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    project_id = fields.Many2one('project.project', string='Project', required=True)
    description = fields.Text(string='Description')
    team_member_ids = fields.One2many('scrum.team_member', 'team_id', string='Team Members')
    sprint_plan_ids = fields.One2many('scrum.sprint_plan', 'team_id', string='Sprint Plans')

class ScrumTeamMember(models.Model):
    _name = 'scrum.team_member'
    _description = 'Scrum Team Member'
    _order = 'team_id, member_type'

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    team_id = fields.Many2one('scrum.team', string='Team', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    member_type = fields.Selection([
        ('product_manager', _('Product Manager')),
        ('agile_coach', _('Agile Coach')),
        ('team_member', _('Team Member')),
        ('stakeholder', _('Stakeholder')),
    ], string='Member Type', required=True)
    member_state = fields.Selection([
        ('active', _('Active')),
        ('inactive', _('Inactive')),
    ], string='Member State', default='active')
    director = fields.Boolean(string='Director',default=False)

    email = fields.Char(string='Email', related='user_id.email', store=True)

    @api.depends('user_id', 'member_type')
    def _compute_name(self):
        for record in self:
            if record.user_id:
                record.name = f"{record.user_id.name} ({dict(self._fields['member_type'].selection).get(record.member_type)})"
            else:
                record.name = ''
