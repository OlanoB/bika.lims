from Products.CMFCore.permissions import View
from AccessControl import getSecurityManager
from bika.lims.permissions import AddClient
from bika.lims.permissions import ManageClients
from Products.CMFCore.utils import getToolByName
from bika.lims.permissions import ManageAnalysisRequests
from bika.lims.browser.bika_listing import BikaListingView
from bika.lims import bikaMessageFactory as _
from operator import itemgetter
from bika.lims.interfaces import IClientFolder
from plone.app.content.browser.interfaces import IFolderContentsView
from bika.lims.browser import BrowserView
from zope.interface import implements
from Products.CMFCore import permissions
import plone,json


class ClientFolderContentsView(BikaListingView):

    implements(IFolderContentsView)

    def __init__(self, context, request):
        super(ClientFolderContentsView, self).__init__(context, request)
        self.contentFilter = {}
        self.icon = "++resource++bika.lims.images/client_big.png"
        self.title = _("Clients")
        self.description = ""
        self.show_sort_column = False
        self.show_select_row = False
        self.show_select_all_checkbox = False
        self.show_select_column = False
        self.pagesize = 25
        request.set('disable_border', 1)

        self.columns = {
            'title': {'title': _('Name')},
            'getClientID': {'title': _('Client ID')},
            'EmailAddress': {'title': _('Email Address')},
            'Phone': {'title': _('Phone')},
            'Fax': {'title': _('Fax')},
        }


        self.review_states = [ # leave these titles and ids alone
            {'id':'default',
             'contentFilter': {'inactive_state':'active'},
             'title': _('Active'),
             'transitions': [{'id':'deactivate'}, ],
             'columns':['title',
                        'getClientID',
                        'EmailAddress',
                        'Phone',
                        'Fax', ]
             },
            {'id':'inactive',
             'title': _('Dormant'),
             'contentFilter': {'inactive_state': 'inactive'},
             'transitions': [{'id':'activate'}, ],
             'columns':['title',
                        'getClientID',
                        'EmailAddress',
                        'Phone',
                        'Fax', ]
             },
            {'id':'all',
             'title': _('All'),
             'contentFilter':{},
             'transitions': [],
             'columns':['title',
                        'getClientID',
                        'EmailAddress',
                        'Phone',
                        'Fax', ]
             },
        ]

    def __call__(self):
        self.context_actions = {}
        mtool = getToolByName(self.context, 'portal_membership')
        if (mtool.checkPermission(AddClient, self.context)):
            self.context_actions[_('Add')] = \
                {'url': 'createObject?type_name=Client',
                 'icon': '++resource++bika.lims.images/add.png'}
        if mtool.checkPermission(ManageClients, self.context):
            self.show_select_column = True
        return super(ClientFolderContentsView, self).__call__()

    def getClientList(self, contentFilter):

        ## Only show clients to which we have Manage AR rights.
        ## (ritamo only sees Happy Hills).
        mtool = getToolByName(self.context, 'portal_membership')
        wf = getToolByName(self.context, 'portal_workflow')

        clients = []
        for client in self.context.objectValues("Client"):
            if not mtool.checkPermission(ManageAnalysisRequests, client):
                continue
            if self.review_state != 'all':
                state = wf.getInfoFor(client, 'inactive_state')
                if self.review_state == 'default' and state != 'active':
                    continue
                if self.review_state == 'inactive' and state != 'inactive':
                    continue
            clients.append(client)
        clients.sort(lambda x,y: cmp(x.Title(),y.Title()))
        return clients

    def folderitems(self):
        self.filter_indexes = None
        self.contentsMethod = self.getClientList
        items = BikaListingView.folderitems(self)
        for x in range(len(items)):
            if not items[x].has_key('obj'): continue
            obj = items[x]['obj']

            items[x]['replace']['title'] = "<a href='%s/batches'>%s</a>"%\
                 (items[x]['url'], items[x]['title'])

            items[x]['EmailAddress'] = obj.getEmailAddress()
            items[x]['replace']['EmailAddress'] = "<a href='%s'>%s</a>"%\
                     ('mailto:%s' % obj.getEmailAddress(),
                      obj.getEmailAddress())
            items[x]['Phone'] = obj.getPhone()
            items[x]['Fax'] = obj.getFax()

        return items


class ajaxGetClients(BrowserView):
    """ Vocabulary source for jquery combo dropdown box
    """
    def __call__(self):
        plone.protect.CheckAuthenticator(self.request)
        searchTerm = 'searchTerm' in self.request and self.request['searchTerm'].lower() or ''
        page = self.request['page']
        nr_rows = self.request['rows']
        sord = self.request['sord']
        sidx = self.request['sidx']
        wf = getToolByName(self.context, 'portal_workflow')

        clients = (x.getObject() for x in self.portal_catalog(portal_type="Client",
                                                              inactive_state = 'active'))
        rows = [{'ClientID': b.getClientID() and b.getClientID() or '',
                 'Title': b.Title() ,
                 'ClientUID': b.UID()} for b in clients
                if b.Title().lower().find(searchTerm) > -1
                or b.getClientID().lower().find(searchTerm) > -1
                or b.Description().lower().find(searchTerm) > -1]

        rows = sorted(rows, cmp=lambda x,y: cmp(x.lower(), y.lower()), key=itemgetter(sidx and sidx or 'Title'))
        if sord == 'desc':
            rows.reverse()
        pages = len(rows) / int(nr_rows)
        pages += divmod(len(rows), int(nr_rows))[1] and 1 or 0
        ret = {'page': page,
               'total': pages,
               'records': len(rows),
               'rows': rows[(int(page) - 1) * int(nr_rows): int(page) * int(nr_rows)]}

        return json.dumps(ret)
