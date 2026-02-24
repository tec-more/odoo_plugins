{
    'name': 'Scrum Project Management',
    'version': '2.0',
    'summary': 'Scrum project management module with AI integration',
    'description': '''
        Scrum Project Management Module with AI Integration
        ==================================================
        This module provides comprehensive Scrum project management functionality for Odoo,
        including product backlog, user stories, sprint backlog, sprint tasks,
        daily meetings, sprint review meetings, and iteration review meetings.
        
        NEW: AI-powered analysis for project quality assessment and requirement compliance.
        - Automated quality scoring and grading
        - Requirement compliance analysis
        - Code review capabilities
        - Sprint effectiveness evaluation
        - Project manager approval workflow
    ''',
    'author': 'hepan',
    'category': 'Services/Project',
    'depends': ['project'],
    'data': [
        'security/ir.model.access.csv',
		'data/sprint_stage_data.xml',
		'views/project_views.xml',
        'views/product_backlog_views.xml',
        'views/user_story_views.xml',
        'views/team_views.xml',
        'views/sprint_plan_views.xml',
        'views/sprint_backlog_views.xml',
        'views/sprint_task_views.xml',
        'views/sprint_stage_views.xml',
        'views/meeting_views.xml',
        'views/ai_analysis_views.xml',
        'views/burndown_chart_views.xml',
        'data/menu.xml',
    ],
    'translation': {
        'addons_dir': 'i18n',
    },
    'installable': True,
    'application': True,
}