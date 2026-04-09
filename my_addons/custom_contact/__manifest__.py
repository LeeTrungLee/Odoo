{
    'name': "custom_contact",
    'summary': "Custom module Contact",
    'description': "Custom module Contact",
    'author': "Lê Trung",
    'website': "",
    'category': 'Custom',
    'version': '19.1',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'contacts', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/res_partner_view.xml',
        'views/agent_tier_view.xml',
    ],
    'installable': True,
}