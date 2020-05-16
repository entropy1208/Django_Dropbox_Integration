import logging
import json


from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse
from django.contrib import messages


from dropbox.dropbox import Dropbox
from dropbox import DropboxOAuth2Flow
from dropbox.oauth import BadRequestException, BadStateException, \
    CsrfException, NotApprovedException, ProviderException


def dropbox_login(request):
    return render(request, "myzapier/dropbox_login.html")


# URL handler for /dropbox-auth-finish
def index(request):
    logger = logging.getLogger('Dropbox OAuth Logger')
    try:
        if 'access_token' in request.session and request.session['access_token']:
            pass
        else:
            auth_result = get_dropbox_auth_flow(request.session).finish(request.GET)
            request.session['access_token'] = auth_result.access_token
            messages.success(request, "You're successfully in!.")
        return redirect('upload', path='')
    except BadRequestException, e:
        return HttpResponse(status=400)
    except BadStateException, e:
        # Start the auth flow again.
        return redirect('dropbox_auth_start')
    except CsrfException, e:
        return HttpResponse(status=403)
    except NotApprovedException, e:
        print 'Not approved?  Why not?'
        return redirect('dropbox_login')
    except ProviderException, e:
        logger.log("Auth error: %s" % (e,))
        return HttpResponse(status=403)


def upload(request, path):
    if request.method == "GET":
        if 'access_token' in request.session and request.session['access_token']:
            dbx = Dropbox(request.session['access_token'])
            if path == '':
                dirs = dbx.files_list_folder('')
            else:
                dirs = dbx.files_list_folder('/' + path)
            paths = []
            for dir in dirs.entries:
                paths.append(dir.path_display[1:])
            request.session['current_path'] = path
            current_path = request.session['current_path']
            return render(request, "myzapier/upload.html",
                          {'paths': paths, 'current_path': current_path})
    if request.method == "POST":
        dbx = Dropbox(request.session['access_token'])
        files = request.FILES.getlist('file1')
        for f in files:
            if request.session['current_path'] == '':
                dbx.files_upload(f.read(), path='/' + f.name, autorename=True)
            else:
                dbx.files_upload(f.read(),
                                 path='/' + request.session['current_path'] + '/' + f.name,
                                 autorename=True)
            messages.success(request, 'Upload Done!.')
        return HttpResponse("Upload Done!")


@csrf_exempt
def action(request, action_name, path):
    if 'access_token' in request.session and request.session['access_token']:
        dbx = Dropbox(request.session['access_token'])
        if action_name == 'get_dirs':
            '''This part gets the valid directories in form of choices for the move and copy operations.'''
            dirs = dbx.files_list_folder('', recursive=True)
            paths = []
            for dir in dirs.entries:
                paths.append(dir.path_display[1:])
            paths = filter(lambda s: not '.' in s, paths)
            dirs = []
            if not '.' in path:
                subpaths = []
                subdirs = dbx.files_list_folder('/' + path, recursive=True)
                for subdir in subdirs.entries:
                    subpaths.append(subdir.path_display[1:])
                paths = list(set(paths) - set(subpaths))
            if request.session['current_path'] != '':
                paths.remove(request.session['current_path'])
            try:
                path.split('/')[1]
            except IndexError:
                pass
            else:
                dirs.append({'value': '', 'text': 'Home'})
            for path_name in paths:
                dir = {}
                dir['value'] = path_name
                dir['text'] = path_name
                dirs.append(dir)
            return HttpResponse(json.dumps(dirs))
        path = '/' + path
        f_name = path.split('/').pop()
        if action_name == 'search':
            results = dbx.files_search(path='', query=request.GET['term'])
            matches = []
            for count, res in enumerate(results.matches):
                match = {}
                match['id'] = count
                match['label'] = res.metadata.path_display
                match['value'] = reverse('upload',
                                         kwargs={'path': res.metadata.path_display[1:]})
                matches.append(match)
            return HttpResponse(json.dumps(matches))
        if action_name == "create_dir":
            if request.session['current_path'] == '':
                dbx.files_create_folder(path=path + request.GET['dir_name'],
                                        autorename=True)
            else:
                dbx.files_create_folder(path=path + '/' + request.GET['dir_name'],
                                        autorename=True)
            msg = 'New Directory %s is created!.' % request.GET['dir_name']
            messages.success(request, msg)
            data = {'success': True, 'msg': msg,
                    'redirect_url': reverse('upload',
                                            kwargs={'path': request.session['current_path']})}
            return HttpResponse(json.dumps(data))
        elif action_name == "download":
            link = dbx.files_get_temporary_link(path).link
            return HttpResponseRedirect(link)
        elif action_name == "delete":
            dbx.files_delete(path)
            messages.success(request, '%s is deleted!.' % path)
            return redirect('upload',
                            path=request.session['current_path'])
        elif action_name == "move":
            if request.GET['to_path'] != '':
                to = '/' + request.GET['to_path'] + '/' + f_name
            else:
                to = '/' + f_name
            dbx.files_move(path, to, autorename=True)
            msg = '%s is moved to %s!.' % (path, to)
            messages.success(request, msg)
            data = {'success': True, 'msg': msg,
                    'redirect_url': reverse('upload',
                                            kwargs={'path': request.GET['to_path']})}
            return HttpResponse(json.dumps(data))
        elif action_name == "copy":
            if request.GET['to_path'] != '':
                to = '/' + request.GET['to_path'] + '/' + f_name
            else:
                to = '/' + f_name
            dbx.files_copy(path, to, autorename=True)
            msg = '%s is copied to %s!.' % (path, to)
            messages.success(request, msg)
            data = {'success': True, 'msg': msg,
                    'redirect_url': reverse('upload',
                                            kwargs={'path': request.GET['to_path']})}
            return HttpResponse(json.dumps(data))


def search(request):
    return render(request, "myzapier/search.html")


def get_dropbox_auth_flow(web_app_session):
    redirect_uri = "http://localhost:8000/zapier/index/"
    return DropboxOAuth2Flow(
        "wz86r6znb1z42dh", "yw5gf9vfxb5leof", redirect_uri, web_app_session,
        "dropbox-auth-csrf-token")


# URL handler for /dropbox-auth-start
def dropbox_auth_start(request):
    authorize_url = get_dropbox_auth_flow(request.session).start()
    return redirect(authorize_url)
