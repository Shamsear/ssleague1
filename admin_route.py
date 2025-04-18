@app.route('/admin/team/<int:team_id>') 
@login_required 
def admin_team_details(team_id): 
    # Redirect to team_squad for now 
    return redirect(url_for('team_squad', team_id=team_id))
