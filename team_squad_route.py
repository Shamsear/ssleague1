@app.route('/team_squad/<int:team_id>')
@login_required
def team_squad(team_id):
