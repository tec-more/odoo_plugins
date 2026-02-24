# -*- coding: utf-8 -*-
import json
import logging
import requests
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ScrumAIAnalysis(models.Model):
    _name = 'scrum.ai_analysis'
    _description = 'Scrum AI Analysis'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, compute='_compute_name', store=True)
    analysis_type = fields.Selection([
        ('quality', _('Quality Assessment')),
        ('requirement', _('Requirement Compliance')),
        ('code_review', _('Code Review')),
        ('sprint_review', _('Sprint Review')),
    ], string='Analysis Type', required=True)
    
    project_id = fields.Many2one('project.project', string='Project', required=True)
    sprint_plan_id = fields.Many2one('scrum.sprint_plan', string='Sprint Plan')
    sprint_backlog_id = fields.Many2one('scrum.sprint_backlog', string='Sprint Backlog')
    user_story_id = fields.Many2one('scrum.user_story', string='User Story')
    sprint_task_id = fields.Many2one('scrum.sprint_task', string='Sprint Task')
    
    status = fields.Selection([
        ('pending', _('Pending')),
        ('analyzing', _('Analyzing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ], string='Status', default='pending', tracking=True)
    
    score = fields.Float(string='AI Score', digits=(5, 2), help='0-100 score from AI analysis')
    grade = fields.Selection([
        ('A', _('Excellent (90-100)')),
        ('B', _('Good (80-89)')),
        ('C', ('Average (70-79)')),
        ('D', _('Poor (60-69)')),
        ('E', _('Very Poor (0-59)')),
    ], string='Grade', compute='_compute_grade', store=True)
    
    ai_feedback = fields.Text(string='AI Feedback')
    suggestions = fields.Text(string='Suggestions')
    issues_found = fields.Text(string='Issues Found')
    
    analysis_data = fields.Json(string='Analysis Data', help='Detailed JSON data from AI')
    analysis_data_formatted = fields.Text(string='Formatted Analysis Data', compute='_compute_analysis_data_formatted')
    
    ai_model = fields.Char(string='AI Model Used', default='gpt-4')
    api_endpoint = fields.Char(string='API Endpoint', default='https://api.openai.com/v1/chat/completions')
    api_key = fields.Char(string='API Key', help='AI API Key for authentication')
    
    analyzed_by = fields.Many2one('res.users', string='Analyzed By', default=lambda self: self.env.user)
    analyzed_date = fields.Datetime(string='Analyzed Date')
    
    approval_status = fields.Selection([
        ('pending', _('Pending Approval')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
    ], string='Approval Status', default='pending', tracking=True)
    approved_by = fields.Many2one('res.users', string='Approved By')
    approved_date = fields.Datetime(string='Approved Date')
    approval_notes = fields.Text(string='Approval Notes')
    
    @api.depends('analysis_type', 'project_id', 'sprint_plan_id', 'sprint_backlog_id', 'user_story_id')
    def _compute_name(self):
        for record in self:
            type_name = dict(self._fields['analysis_type'].selection).get(record.analysis_type, '')
            if record.sprint_task_id:
                record.name = f"{type_name} - {record.sprint_task_id.name}"
            elif record.user_story_id:
                record.name = f"{type_name} - {record.user_story_id.name}"
            elif record.sprint_backlog_id:
                record.name = f"{type_name} - {record.sprint_backlog_id.name}"
            elif record.sprint_plan_id:
                record.name = f"{type_name} - {record.sprint_plan_id.name}"
            else:
                record.name = f"{type_name} - {record.project_id.name}"
    
    @api.depends('score')
    def _compute_grade(self):
        for record in self:
            if record.score >= 90:
                record.grade = 'A'
            elif record.score >= 80:
                record.grade = 'B'
            elif record.score >= 70:
                record.grade = 'C'
            elif record.score >= 60:
                record.grade = 'D'
            else:
                record.grade = 'E'
    
    @api.depends('analysis_data')
    def _compute_analysis_data_formatted(self):
        for record in self:
            if record.analysis_data:
                record.analysis_data_formatted = json.dumps(record.analysis_data, indent=2, ensure_ascii=False)
            else:
                record.analysis_data_formatted = False
    
    def action_analyze(self):
        self.ensure_one()
        self.write({
            'status': 'analyzing',
            'analyzed_date': datetime.now()
        })
        
        try:
            context_data = self._prepare_analysis_context()
            prompt = self._generate_prompt(context_data)
            
            ai_response = self._call_ai_service(prompt)
            
            result = self._parse_ai_response(ai_response)
            
            self.write({
                'status': 'completed',
                'score': result.get('score', 0.0),
                'ai_feedback': result.get('feedback', ''),
                'suggestions': result.get('suggestions', ''),
                'issues_found': result.get('issues', ''),
                'analysis_data': result.get('details', {}),
            })
            
        except Exception as e:
            _logger.error('AI Analysis failed: %s', e)
            self.write({
                'status': 'failed',
                'ai_feedback': f'Analysis failed: {str(e)}'
            })
            raise UserError(_('AI Analysis failed: %s') % e)
    
    def _prepare_analysis_context(self):
        self.ensure_one()
        context = {
            'project_name': self.project_id.name,
            'project_description': getattr(self.project_id, 'description', ''),
            'analysis_type': self.analysis_type,
        }
        
        if self.sprint_task_id:
            task = self.sprint_task_id
            context.update({
                'task_name': task.name,
                'task_description': task.description,
                'task_status': task.sprint_stage_id.name if task.sprint_stage_id else '',
                'estimated_hours': task.estimated_hours,
                'actual_hours': task.actual_hours,
            })
            if task.user_story_id:
                context.update({
                    'user_story': task.user_story_id.name,
                    'user_story_description': task.user_story_id.description,
                    'acceptance_criteria': task.user_story_id.acceptance_criteria,
                })
        
        elif self.user_story_id:
            story = self.user_story_id
            context.update({
                'user_story': story.name,
                'user_story_description': story.description,
                'acceptance_criteria': story.acceptance_criteria,
                'story_status': story.status,
                'estimated_story_points': story.estimated_story_points,
                'total_tasks': story.total_tasks,
                'completed_tasks': story.completed_tasks,
                'task_completion_percentage': story.task_completion_percentage,
            })
        
        elif self.sprint_backlog_id:
            backlog = self.sprint_backlog_id
            context.update({
                'sprint_backlog_name': backlog.name,
                'sprint_goal': backlog.goal,
                'backlog_status': backlog.status,
                'total_tasks': backlog.total_tasks,
                'completed_tasks': backlog.completed_tasks,
                'completion_percentage': backlog.completion_percentage,
            })
        
        elif self.sprint_plan_id:
            plan = self.sprint_plan_id
            context.update({
                'sprint_name': plan.name,
                'sprint_goal': plan.goal,
                'iteration_number': plan.iteration_number,
                'start_date': plan.start_date,
                'end_date': plan.end_date,
                'status': plan.status,
                'total_backlogs': plan.total_backlogs,
                'completed_backlogs': plan.completed_backlogs,
                'backlog_completion_percentage': plan.backlog_completion_percentage,
            })
        
        return context
    
    def _generate_prompt(self, context):
        self.ensure_one()
        
        prompts = {
            'quality': self._generate_quality_prompt(context),
            'requirement': self._generate_requirement_prompt(context),
            'code_review': self._generate_code_review_prompt(context),
            'sprint_review': self._generate_sprint_review_prompt(context),
        }
        
        return prompts.get(self.analysis_type, '')
    
    def _generate_quality_prompt(self, context):
        prompt = f"""
        As an AI quality analyst, please evaluate the following Scrum project component for quality:
        
        Project: {context['project_name']}
        Type: {context['analysis_type']}
        
        """
        if 'task_name' in context:
            prompt += f"""
            Task: {context['task_name']}
            Description: {context['task_description']}
            Status: {context['task_status']}
            Estimated Hours: {context['estimated_hours']}
            Actual Hours: {context['actual_hours']}
            User Story: {context.get('user_story', 'N/A')}
            Acceptance Criteria: {context.get('acceptance_criteria', 'N/A')}
            """
        elif 'user_story' in context:
            prompt += f"""
            User Story: {context['user_story']}
            Description: {context['user_story_description']}
            Acceptance Criteria: {context['acceptance_criteria']}
            Status: {context['story_status']}
            Story Points: {context['estimated_story_points']}
            Task Completion: {context['task_completion_percentage']}% ({context['completed_tasks']}/{context['total_tasks']} tasks)
            """
        
        prompt += """
        
        Please provide:
        1. A quality score from 0-100 (considering completeness, clarity, alignment with Scrum practices)
        2. Detailed feedback on quality aspects
        3. Specific suggestions for improvement
        4. List of any issues or concerns found
        
        Respond in JSON format with the following structure:
        {
            "score": number,
            "feedback": "string",
            "suggestions": "string",
            "issues": "string",
            "details": {
                "completeness": number,
                "clarity": number,
                "scrum_alignment": number,
                "quality_factors": ["string"]
            }
        }
        """
        return prompt
    
    def _generate_requirement_prompt(self, context):
        prompt = f"""
        As an AI requirement analyst, please evaluate the following Scrum component for requirement compliance:
        
        Project: {context['project_name']}
        
        """
        if 'user_story' in context:
            prompt += f"""
            User Story: {context['user_story']}
            Description: {context['user_story_description']}
            Acceptance Criteria: {context['acceptance_criteria']}
            """
        elif 'task_name' in context:
            prompt += f"""
            Task: {context['task_name']}
            Description: {context['task_description']}
            User Story Acceptance Criteria: {context.get('acceptance_criteria', 'N/A')}
            """
        
        prompt += """
        
        Please evaluate:
        1. Whether requirements are clearly defined
        2. If acceptance criteria are measurable and testable
        3. Completeness of the requirement
        4. Alignment with business needs
        
        Respond in JSON format with:
        {
            "score": number,
            "feedback": "string",
            "suggestions": "string",
            "issues": "string",
            "details": {
                "clarity": number,
                "measurability": number,
                "completeness": number,
                "business_alignment": number
            }
        }
        """
        return prompt
    
    def _generate_code_review_prompt(self, context):
        prompt = f"""
        As an AI code reviewer, please evaluate the implementation quality:
        
        Task: {context.get('task_name', 'N/A')}
        User Story: {context.get('user_story', 'N/A')}
        
        Based on the task description and acceptance criteria, provide:
        1. Quality score (0-100)
        2. Code quality assessment
        3. Potential issues or bugs
        4. Best practices recommendations
        
        Respond in JSON format:
        {
            "score": number,
            "feedback": "string",
            "suggestions": "string",
            "issues": "string",
            "details": {
                "code_quality": number,
                "maintainability": number,
                "security": number,
                "performance": number
            }
        }
        """
        return prompt
    
    def _generate_sprint_review_prompt(self, context):
        prompt = f"""
        As an AI sprint reviewer, please evaluate the sprint completion:
        
        Sprint: {context.get('sprint_name', context['project_name'])}
        Goal: {context.get('sprint_goal', 'N/A')}
        Status: {context.get('status', 'N/A')}
        Completion: {context.get('backlog_completion_percentage', context.get('completion_percentage', 0))}%
        
        Please evaluate:
        1. Sprint goal achievement
        2. Delivery quality
        3. Team performance
        4. Process effectiveness
        
        Respond in JSON format:
        {
            "score": number,
            "feedback": "string",
            "suggestions": "string",
            "issues": "string",
            "details": {
                "goal_achievement": number,
                "delivery_quality": number,
                "team_performance": number,
                "process_effectiveness": number
            }
        }
        """
        return prompt
    
    def _call_ai_service(self, prompt):
        self.ensure_one()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key or self.env.context.get('ai_api_key', '')}'
        }
        
        data = {
            'model': self.ai_model,
            'messages': [
                {'role': 'system', 'content': 'You are an expert Scrum and software development analyst.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3,
            'response_format': {'type': 'json_object'}
        }
        
        response = requests.post(self.api_endpoint, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
    def _parse_ai_response(self, response):
        try:
            data = json.loads(response)
            return data
        except json.JSONDecodeError:
            return {
                'score': 50.0,
                'feedback': 'Unable to parse AI response',
                'suggestions': '',
                'issues': 'JSON parsing error',
                'details': {}
            }
    
    def action_approve(self):
        self.ensure_one()
        if self.status != 'completed':
            raise UserError(_('Can only approve completed analyses.'))
        self.write({
            'approval_status': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': datetime.now()
        })
    
    def action_reject(self):
        self.ensure_one()
        self.write({
            'approval_status': 'rejected',
            'approved_by': self.env.user.id,
            'approved_date': datetime.now()
        })
    
    def action_resend_for_analysis(self):
        self.ensure_one()
        self.write({
            'status': 'pending',
            'approval_status': 'pending',
            'score': 0.0,
            'ai_feedback': '',
            'suggestions': '',
            'issues_found': '',
            'analysis_data': {},
        })