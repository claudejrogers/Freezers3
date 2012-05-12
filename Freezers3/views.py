from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import redirect
from django.contrib import auth
from django.contrib.auth.decorators import login_required

@login_required
def logout_view(request):
    auth.logout(request)
    return HttpResponseRedirect('/accounts/login/')

def root_view(request):
    if request.user.is_authenticated():
        return redirect('/freezers/home/%s/' % request.user.id)
    return redirect('/accounts/login/')
