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
    
    ai_analysis_ids = fields.One2many('scrum.ai_analysis', 'project_id', string='AI Analyses')
    
    overall_quality_score = fields.Float(string='Overall Quality Score', digits=(5, 2), compute='_compute_quality_metrics', store=True)
    overall_grade = fields.Selection([
        ('A', _('Excellent (90-100)')),
        ('B', _('Good (80-89)')),
        ('C', _('Average (70-79)')),
        ('D', _('Poor (60-69)')),
        ('E', _('Very Poor (0-59)')),
    ], string='Overall Grade', compute='_compute_quality_metrics', store=True)
    
    requirement_compliance_score = fields.Float(string='Requirement Compliance Score', digits=(5, 2), compute='_compute_quality_metrics', store=True)
    code_quality_score = fields.Float(string='Code Quality Score', digits=(5, 2), compute='_compute_quality_metrics', store=True)
    sprint_effectiveness_score = fields.Float(string='Sprint Effectiveness Score', digits=(5, 2), compute='_compute_quality_metrics', store=True)
    
    last_analysis_date = fields.Datetime(string='Last Analysis Date', compute='_compute_last_analysis', store=True)
    ai_feedback_summary = fields.Text(string='AI Feedback Summary', compute='_compute_ai_feedback_summary')
    
    auto_analyze = fields.Boolean(string='Auto Analyze on Sprint Completion', default=False)
    minimum_quality_threshold = fields.Float(string='Minimum Quality Threshold', default=70.0, help='Minimum quality score required for project to pass')
    
    quality_passed = fields.Boolean(string='Quality Passed', compute='_compute_quality_passed', store=True)
    
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
    
    @api.depends('ai_analysis_ids', 'ai_analysis_ids.score', 'ai_analysis_ids.status', 'ai_analysis_ids.approval_status')
    def _compute_quality_metrics(self):
        for record in self:
            analyses = record.ai_analysis_ids.filtered(lambda a: a.status == 'completed' and a.approval_status == 'approved')
            
            if not analyses:
                record.overall_quality_score = 0.0
                record.overall_grade = 'E'
                record.requirement_compliance_score = 0.0
                record.code_quality_score = 0.0
                record.sprint_effectiveness_score = 0.0
                continue
            
            quality_scores = analyses.filtered(lambda a: a.analysis_type == 'quality').mapped('score')
            requirement_scores = analyses.filtered(lambda a: a.analysis_type == 'requirement').mapped('score')
            code_scores = analyses.filtered(lambda a: a.analysis_type == 'code_review').mapped('score')
            sprint_scores = analyses.filtered(lambda a: a.analysis_type == 'sprint_review').mapped('score')
            
            record.overall_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            record.requirement_compliance_score = sum(requirement_scores) / len(requirement_scores) if requirement_scores else 0.0
            record.code_quality_score = sum(code_scores) / len(code_scores) if code_scores else 0.0
            record.sprint_effectiveness_score = sum(sprint_scores) / len(sprint_scores) if sprint_scores else 0.0
            
            if record.overall_quality_score >= 90:
                record.overall_grade = 'A'
            elif record.overall_quality_score >= 80:
                record.overall_grade = 'B'
            elif record.overall_quality_score >= 70:
                record.overall_grade = 'C'
            elif record.overall_quality_score >= 60:
                record.overall_grade = 'D'
            else:
                record.overall_grade = 'E'
    
    @api.depends('ai_analysis_ids', 'ai_analysis_ids.analyzed_date')
    def _compute_last_analysis(self):
        for record in self:
            analyses = record.ai_analysis_ids.filtered(lambda a: a.analyzed_date)
            record.last_analysis_date = max(analyses.mapped('analyzed_date')) if analyses else False
    
    @api.depends('ai_analysis_ids', 'ai_analysis_ids.ai_feedback')
    def _compute_ai_feedback_summary(self):
        for record in self:
            recent_analyses = record.ai_analysis_ids.search([
                ('project_id', '=', record.id),
                ('status', '=', 'completed'),
                ('approval_status', '=', 'approved')
            ], order='analyzed_date desc', limit=5)
            
            feedback_list = [a.ai_feedback for a in recent_analyses if a.ai_feedback]
            record.ai_feedback_summary = '\n\n'.join(feedback_list) if feedback_list else ''
    
    @api.depends('overall_quality_score', 'minimum_quality_threshold')
    def _compute_quality_passed(self):
        for record in self:
            record.quality_passed = record.overall_quality_score >= record.minimum_quality_threshold if record.overall_quality_score > 0 else False
    
    sprint_count = fields.Integer(string='Sprint Count', compute='_compute_sprint_count', store=True)
    team_member_count = fields.Integer(string='Team Member Count', compute='_compute_team_member_count', store=True)
    active_sprint_count = fields.Integer(string='Active Sprint Count', compute='_compute_active_sprint_count', store=True)
    
    def action_analyze_project_quality(self):
        self.ensure_one()
        return {
            'name': _('Analyze Project Quality'),
            'type': 'ir.actions.act_window',
            'res_model': 'scrum.ai_analysis',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
                'default_analysis_type': 'quality',
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
                'default_project_id': self.id,
                'default_analysis_type': 'requirement',
            },
        }
    
    def action_view_analyses(self):
        self.ensure_one()
        return {
            'name': _('AI Analyses'),
            'type': 'ir.actions.act_window',
            'res_model': 'scrum.ai_analysis',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
        }
