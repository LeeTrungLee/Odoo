{
    'name': "custom_product",
    'summary': "Custom Sản phẩm",
    'description': """Custom Sản phẩm""",
    'author': "Le Trung",
    'website': "",
    'category': 'Custom',
    'version': '19.1',
    'depends': ['base', 'product', 'sale'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/product_template_view.xml',
        'views/product_attribute_view.xml',
        'views/product_category_view.xml',
    ],
}
