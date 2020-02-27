from django.db import connections
from django_eveonline_connector.utilities.esi.universe import get_type_id, get_station_id, get_group_id, resolve_names, get_category_id
import logging

logger = logging.getLogger(__name__)


def resolve_type_id_to_type_name(type_id):
    from django.db.utils import ConnectionDoesNotExist
    from django_eveonline_connector.utilities.esi.universe import get_type_id
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute(
                "select typeName from invTypes where typeID = %s" % type_id)
            row = str(cursor.fetchone()[0])
        return row
    except ConnectionDoesNotExist as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
    except Exception as e:
        logger.error(
            "Error resolving EVE type_id(%s) to type_name: %s" % (type_id, e))

    logger.warning("Resolving type_id using ESI")
    return get_type_id(type_id)['name']

def resolve_type_name_to_type_id(type_name):
    from django.db.utils import ConnectionDoesNotExist
    from django_eveonline_connector.utilities.esi.universe import resolve_names
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute(
                "select typeID from invTypes where typeName = %s" % type_name)
            row = str(cursor.fetchone()[0])
        return row
    except ConnectionDoesNotExist as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
    except Exception as e:
        logger.error(
            "Error resolving EVE type_name(%s) to type_id: %s" % (type_name, e))

    logger.warning("Resolving type_name using ESI")
    return resolve_names(type_name)['inventory_types'][0]['id']


def resolve_type_id_to_group_id(type_id):
    from django.db.utils import ConnectionDoesNotExist
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute(
                "select groupID from invTypes where typeID = %s" % type_id)
            row = str(cursor.fetchone()[0])
        return row
    except ConnectionDoesNotExist as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
    except Exception as e:
        logger.error(
            "Error resolving EVE type_id(%s) to group_id: %s" % (type_id, e))
    logger.warning("Resolving group_id using ESI")
    return get_type_id(type_id)['group_id']

def resolve_type_id_to_category_name(type_id):
    try:
        category_id = resolve_type_id_to_category_id(type_id)
    except Exception as e:
        logger.error("Failed to resolve %s. \n%s" % (type_id, e))
        return "Unknown Category"

def resolve_group_id_to_group_name(group_id):
    from django.db.utils import ConnectionDoesNotExist
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute(
                "select groupName from invGroups where groupID = %s" % group_id)
            row = str(cursor.fetchone()[0])
        return row
    except ConnectionDoesNotExist as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
    except Exception as e:
        logger.error(
            "Error resolving EVE type_id(%s) to group_id: %s" % (group_id, e))
    logger.warning("Resolving group_id using ESI")
    return get_group_id(group_id)['name']


def resolve_type_id_to_group_name(type_id):
    group_id = resolve_type_id_to_group_id(type_id)
    return resolve_group_id_to_group_name(group_id)


def resolve_group_id_to_category_id(group_id):
    from django.db.utils import ConnectionDoesNotExist
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute(
                "select categoryID from invGroups where groupID = %s" % group_id)
            row = str(cursor.fetchone()[0])
        return row
    except ConnectionDoesNotExist as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
    except Exception as e:
        logger.error(
            "Error resolving EVE group_id(%s) to category_id: %s" % (group_id, e))
    logger.warning("Resolving category_id using ESI")
    return get_group_id(group_id)['category_id']

def resolve_category_id_to_category_name(category_id):
    from django.db.utils import ConnectionDoesNotExist
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute(
                "select categoryName from invCategories where categoryID = %s" % category_id)
            row = str(cursor.fetchone()[0])
        return row
    except ConnectionDoesNotExist as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
    except Exception as e:
        logger.error(
            "Error resolving EVE category_id(%s) to category_name: %s" % (category_id, e))
    logger.warning("Resolving category_id using ESI")
    return get_category_id(category_id)['name']


def resolve_type_id_to_category_id(type_id):
    group_id = resolve_type_id_to_group_id(type_id)
    category_id = resolve_group_id_to_category_id(group_id)
    return int(category_id)


def resolve_location_id_to_station(location_id):
    from django.db.utils import ConnectionDoesNotExist
    try:
        with connections['eve_static'].cursor() as cursor:
            query = "select stationName from staStations where stationID = %s" % location_id
            cursor.execute(query)
            row = str(cursor.fetchone()[0])
        return row
    except ConnectionDoesNotExist as e:
        logger.error(
            "EVE static database is not installed: massively slows down your tasks")
    except Exception as e:
        logger.error(e)

    logger.warning("Resolving location_id using ESI")
    return get_station_id(location_id)['name']
