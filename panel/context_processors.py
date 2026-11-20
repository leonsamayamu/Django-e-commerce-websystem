from accounts.roles import ROLE_LABELS, caps_for, role_of


def panel(request):
    """`caps` (set of capability names) and `staff_role_label` for staff templates."""
    user = request.user
    if not (user.is_authenticated and user.is_staff):
        return {}
    role = role_of(user)
    return {"caps": caps_for(user), "staff_role_label": "Admin" if role == "admin" else ROLE_LABELS.get(role, "")}
