from django import template
from django.template.defaultfilters import stringfilter
from django.core.urlresolvers import reverse


register = template.Library()


@register.filter('onlyname', is_safe=True)
@stringfilter
def only_name(value):  # Only one argument.
    """Returns only filename from its whole absolute path"""
    return value.split('/').pop()


@register.inclusion_tag('myzapier/breadcrumbs.html', takes_context=True)
def show_breadcrumbs(context):
    my_crumbs = []
    link = context['current_path']
    dirs = link.split('/')
    crumb = '<a href="{}">{}</a>'.format(reverse('upload',
                                                 kwargs={'path': ''}), "Home")
    my_crumbs.append(crumb)
    if len(dirs) == 1 and dirs[0] == '':
        return {'my_crumbs': my_crumbs[0]}
    else:
        for index, dir in enumerate(dirs):
            if index == len(dirs)-1:
                crumb = '<span>{}</span>'.format(dir)
                # the current bread crumb should not be a link.
            else:
                crumb = '<a href="{}">{}</a>'.format(reverse('upload',
                                                             kwargs={'path': dir}), dir)
            my_crumbs.append(crumb)
        my_crumbs = ' &gt; '.join(my_crumbs)
        return {'my_crumbs': my_crumbs}
