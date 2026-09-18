from app.models import Alert,Log
def notify(db,voyage_id,kind,message):
    row=Alert(voyage_id=voyage_id,type=kind,message=message);db.add(row);return row
def log(db,user_id,action,detail=''):
    db.add(Log(user_id=user_id,action=action,detail=detail))
