# -*- coding: utf-8 -*-
from odoo import models, fields, api ,_

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
    assigned_to = fields.Many2one('res.users', string='Assigned To')
    sprint_task_ids = fields.One2many('scrum.sprint_task', 'user_story_id', string='Sprint Tasks')
    sprint_backlog_id = fields.Many2one('scrum.sprint_backlog', string='Sprint Backlog')
    
    @api.onchange('product_backlog_id')
    def _onchange_product_backlog_id(self):
        if self.product_backlog_id:
            self.project_id = self.product_backlog_id.project_id

    project_id = fields.Many2one('project.project', string='Project', related='product_backlog_id.project_id', store=True, readonly=True)