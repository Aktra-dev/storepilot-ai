import sys
sys.path.insert(0, 'D:/storepilot-ai')
try:
    from app.modules.auth.models import User
    from app.modules.products.models import Product
    from app.modules.inventory.models import Inventory
    from app.modules.sales.models import Sale
    from app.modules.tasks.models import Task
    from app.modules.approvals.models import Approval
    from app.modules.operational_analysis.models import OperationalAnalysis, OperationalFinding
    print('✅ All models import OK')
except Exception as e:
    print('❌ Import error:', e)
    import traceback
    traceback.print_exc()