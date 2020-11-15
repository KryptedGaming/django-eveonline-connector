from django.shortcuts import render, redirect
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.generic import TemplateView
from django_eveonline_connector.models import EveCharacter, EveEntity
from django_eveonline_connector.models import EveAsset, EveJumpClone, EveContact, EveContract, EveSkill, EveJournalEntry, EveTransaction
from django_eveonline_connector.models import EveClient
from django_eveonline_connector.utilities.esi.universe import resolve_id
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.html import escape
import json 

# Utilities 
@login_required
def get_entity_info(request):
    external_id = None 
    if 'external_id' not in request.GET:
        return HttpResponse(status=400)
    else:
        external_id = request.GET['external_id']
    print(external_id)
    
    entity = resolve_id(external_id)

    if not entity:
        return HttpResponse(status=404)

    if entity['type'] == "character":
        response = EveClient.call('get_characters_character_id', character_id=external_id).data
        return JsonResponse({
            "type": "character",
            "name": response['name'],
            "external_id": external_id,
        })
    elif entity['type'] == "corporation":
        response = EveClient.call('get_corporations_corporation_id', corporation_id=external_id).data
        return JsonResponse({
            "type": "corporation",
            "name": response['name'],
            "ticker": response['ticker'],
            "external_id": external_id,
            "alliance_id": response['alliance_id'],
        })
    elif entity['type'] == "alliance":
        response = EveClient.call('get_alliances_alliance_id', alliance_id=external_id).data
        return JsonResponse({
            "type": "alliance", 
            "name": response['name'],
            "ticker": response['ticker'],
            "external_id": external_id,
        })
    else:
        return HttpResponse(status=500)



# Character Lookups
@login_required
@permission_required('django_eveonline_connector.view_eveasset', raise_exception=True)
def get_assets(request):
    if 'external_id' not in request.GET:
        return HttpResponse(status=400)
    if not EveEntity.objects.filter(external_id=request.GET.get('external_id')):
        return HttpResponse(status=404)
    return AssetJson.as_view()(request)


@login_required
@permission_required('django_eveonline_connector.view_evejumpclone', raise_exception=True)
def get_clones(request):
    if 'external_id' not in request.GET:
        return HttpResponse(status=400)
    if not EveEntity.objects.filter(external_id=request.GET.get('external_id')):
        return HttpResponse(status=404)
    return CloneJson.as_view()(request)


@login_required
@permission_required('django_eveonline_connector.view_evecontact', raise_exception=True)
def get_contacts(request):
    if 'external_id' not in request.GET:
        return HttpResponse(status=400)
    if not EveEntity.objects.filter(external_id=request.GET.get('external_id')):
        return HttpResponse(status=404)
    return ContactJson.as_view()(request)


@login_required
@permission_required('django_eveonline_connector.view_evecontract', raise_exception=True)
def get_contracts(request):
    if 'external_id' not in request.GET:
        return HttpResponse(status=400)
    if not EveEntity.objects.filter(external_id=request.GET.get('external_id')):
        return HttpResponse(status=404)
    return ContractJson.as_view()(request)


@login_required
@permission_required('django_eveonline_connector.view_evejournalentry', raise_exception=True)
def get_journal(request):
    if 'external_id' not in request.GET:
        return HttpResponse(status=400)
    if not EveEntity.objects.filter(external_id=request.GET.get('external_id')):
        return HttpResponse(status=404)
    return JournalJson.as_view()(request)


@login_required
@permission_required('django_eveonline_connector.view_evetransaction', raise_exception=True)
def get_transactions(request):
    if 'external_id' not in request.GET:
        return HttpResponse(status=400)
    if not EveEntity.objects.filter(external_id=request.GET.get('external_id')):
        return HttpResponse(status=404)
    return TransactionJson.as_view()(request)


# JSON Class Views
class AssetJson(BaseDatatableView):
    model = EveAsset
    columns = ['item_name', 'location_name', 'quantity']
    order_columns = ['item_name', 'location_name', 'quantity']

    def filter_queryset(self, qs):
        # implement searching
        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(Q(item_name__istartswith=search) | Q(location_name__istartswith=search))

        # return character
        external_id = self.request.GET.get('external_id')
        return qs.filter(entity__external_id=external_id, location_flag="Hangar")

    def prepare_results(self, qs):
        json_data = []
        for item in qs:
            json_data.append([
                item.item_name,
                item.location_name,
                item.quantity,
            ])
        return json_data


class CloneJson(BaseDatatableView):
    model = EveJumpClone
    columns = ['location', 'implants']
    order_columns = ['location', 'implants']

    def filter_queryset(self, qs):
        # implement searching
        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(Q(location__istartswith=search)
                           | Q(implants__contains=search))

        # return character
        external_id = self.request.GET.get('external_id')
        return qs.filter(Q(entity__external_id=external_id))

    def prepare_results(self, qs):
        json_data = []
        for item in qs:
            json_data.append([
                item.location,
                item.implants.replace(",", "<br>"),
            ])
        return json_data


class ContactJson(BaseDatatableView):
    model = EveContact
    columns = ['name', 'contact_type', 'standing']
    order_columns = ['name', 'contact_type', 'standing']

    def filter_queryset(self, qs):
        # implement searching
        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(
                Q(contact_name__istartswith=search) | 
                Q(contact_type__istartswith=search)
                )

        # return character
        external_id = self.request.GET.get('external_id')
        return qs.filter(Q(entity__external_id=external_id))

    def prepare_results(self, qs):
        json_data = []
        for item in qs:
            json_data.append([
                '<a onclick="setModalID(%s)" href="#" data-toggle="modal" data-target="#entityModal">%s</a>' % (item.contact_id, item.contact_name),
                item.contact_type.title(),
                item.standing
            ])
        return json_data


class ContractJson(BaseDatatableView):
    model = EveContract
    columns = ['date_issued', 'status',
               'type', 'issuer_name', 'assignee_name', 'items']
    order_columns = ['date_issued', 'status',
                     'type', 'issuer_name', 'assignee_name', 'items']

    def filter_queryset(self, qs):
        # implement searching
        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(Q(issuer_name__istartswith=search) |
                           Q(assignee_name__istartswith=search) |
                           Q(type__istartswith=search) | 
                           Q(status__istartswith=search)
                           )

        # return character
        external_id = self.request.GET.get('external_id')
        return qs.filter(Q(entity__external_id=external_id))

    def prepare_results(self, qs):
        json_data = []
        for contract in qs:
            date_issued = contract.date_issued
            status = contract.status
            type = contract.type
            issuer_name = contract.issuer_name
            if contract.acceptor_name:
                assignee_name = contract.acceptor_name
            elif contract.issued_to:
                assignee_name = contract.assignee_name
            else:
                assignee_name = "Public"
            actions = """
                <button class="text-center btn btn-success" data-toggle="modal" data-target="#view_%s"><i class="fa fa-eye"></i></button>
                <div class="modal fade col-md-12" id="view_%s" data-backdrop="false">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h4>View Contract</h4>
                            </div>
                            <div class="modal-body">
                               <p>%s</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                </div>
            """ % (contract.pk, contract.pk, contract.items.replace("\n", "<br>"))

            json_data.append([
                date_issued.strftime("%m-%d-%Y"),
                status,
                type.replace("_", " ").upper(),
                issuer_name,
                assignee_name,
                actions
            ])
        return json_data


class JournalJson(BaseDatatableView):
    model = EveJournalEntry
    columns = ['date', 'ref_type', 'first_party_name', 'second_party_name', 'amount']
    order_columns = ['date', 'ref_type', 'first_party_name', 'second_party_name', 'amount']

    def filter_queryset(self, qs):
        # implement searching
        search = self.request.GET.get('search[value]', None)
        if search:
            qs = qs.filter(Q(ref_type__istartswith=search) |
                           Q(first_party_name__istartswith=search) |
                           Q(second_party_name__istartswith=search))

        # return character
        external_id = self.request.GET.get('external_id')
        return qs.filter(Q(entity__external_id=external_id))

    def prepare_results(self, qs):
        json_data = []
        # resolve custom template responses
        for entry in qs:
            first_party_ext = "jpg"
            second_party_ext = "jpg"
            if entry.first_party_type == "corporation":
                first_party_ext = "png"
            if entry.second_party_type == "corporation":
                second_party_ext = "png"
            # add avatars for first party field
            if entry.first_party_type == "corporation" or entry.first_party_type == "character":
                entry_first_party = """
                <img width="32px" src="https://imageserver.eveonline.com/%s/%s_64.%s" class="img-circle img-bordered-sm" alt="Avatar">
                %s 
                """ % (entry.first_party_type.title(), entry.first_party_id, first_party_ext, entry.first_party_name)
            else:
                entry_first_party = entry.ref_type
            # add avatars for second party field
            if entry.second_party_type == "corporation" or entry.second_party_type == "character":
                entry_second_party = """
                <img width="32px" src="https://imageserver.eveonline.com/%s/%s_64.%s" class="img-circle img-bordered-sm" alt="Avatar">
                %s 
                """ % (entry.second_party_type.title(), entry.second_party_id, second_party_ext, entry.second_party_name)
            else:
                entry.second_party_name = entry.ref_type
            # clean up amount html
            if entry.amount < 0:
                amount_color = "red"
            else:
                amount_color = "green"
            entry_amount = """
                <p><span style="color: %s">%s</span></p>
            """ % (amount_color, f'{entry.amount:,}')

            json_data.append([
                entry.date.strftime("%m-%d-%Y"),
                entry.ref_type.title(),
                entry_first_party,
                entry_second_party,
                entry_amount,
            ])

        return json_data


class TransactionJson(BaseDatatableView):
    model = EveTransaction
    columns = ['client_name', 'item_name', 'quantity', 'unit_price']
    order_columns = ['client_name', 'item_name', 'quantity', 'unit_price']

    def filter_queryset(self, qs):
        # implement searching
        search = self.request.GET.get('search[unit_price]', None)
        if search:
            qs = qs.filter(Q(item_name__istartswith=search) |
                           Q(client__istartswith=search)
                           )

        # return character
        external_id = self.request.GET.get('external_id')
        return qs.filter(Q(entity__external_id=external_id))

    def prepare_results(self, qs):
        json_data = []
        # resolve custom template responses
        for transaction in qs:
            client_ext = "jpg"
            if transaction.client_type == "corporation":
                client_ext = "png"
            # add avatars for client_name
            if transaction.client_type.lower() == "corporation" or transaction.client_type.lower() == "character":
                transaction_client = """
                <img width="32px" src="https://imageserver.eveonline.com/%s/%s_64.%s" class="img-circle img-bordered-sm" alt="Avatar">
                %s 
                """ % (transaction.client_type.title(), transaction.client_id, client_ext, transaction.client_name)
            else:
                transaction_client = transaction.client_type
            # clean up unit_price html
            if transaction.is_buy:
                amount_color = "red"
            else:
                amount_color = "green"
            transaction_amount = """
                <p><span style="color: %s">%s</span></p>
            """ % (amount_color, f'{transaction.unit_price:,}')

            json_data.append([
                transaction_client,
                transaction.item_name,
                transaction.quantity,
                transaction_amount,
            ])

        return json_data
