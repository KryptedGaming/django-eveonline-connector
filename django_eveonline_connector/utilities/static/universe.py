from django.db import connections
from django_eveonline_connector.utilities.esi.universe import *
from django.db.utils import ConnectionDoesNotExist, OperationalError
import logging

logger = logging.getLogger(__name__)


def resolve_type_id_to_type_name(type_id):
    from django_eveonline_connector.utilities.esi.universe import get_type_id
    type_name = None
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute(
                "select typeName from invTypes where typeID = %s" % type_id)
            row = str(cursor.fetchone()[0])
        return row 
    except TypeError as e:
        logger.warning("Unable to find type_id(%s) in static database" % type_id)
    except ConnectionDoesNotExist as e:
        logger.warning("EVE static database is not installed: this slows down your tasks")
        raise(e)
    except OperationalError as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
        raise(e)
    except Exception as e:
        logger.exception(e)

    logger.warning("Resolving type_id (%s) using ESI" % type_id)
    response = get_type_id(type_id)
    
    if 'name' in response:
        type_name=response['name']
    
    if not type_name:
        logger.error("Failed to resolve type_id (%s) to type_name" % type_id)
    
    return type_name

def resolve_type_name_to_type_id(type_name):
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
        raise(e)
    except OperationalError as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
        raise(e)
    except Exception as e:
        logger.exception(e)
        

    logger.warning("Resolving type_name using ESI")
    type_id = resolve_names(type_name)['inventory_types'][0]['id']
    if not type_id:
        logger.error(
            "Error resolving EVE type_name(%s) to type_id" % type_name)
    return type_id

def resolve_type_id_to_group_id(type_id):
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute(
                "select groupID from invTypes where typeID = %s" % type_id)
            row = str(cursor.fetchone()[0])
        return row
    except ConnectionDoesNotExist as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
        raise(e)
    except OperationalError as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
        raise(e)
    except Exception as e:
        logger.exception(e)
        
    logger.warning("Resolving group_id using ESI")

    group_id = get_type_id(type_id)['group_id']
    if not group_id:
        logger.error("Error resolving EVE type_id(%s) to group_id" % type_id)
    return group_id 

def resolve_type_id_to_category_name(type_id):
    category_id = resolve_type_id_to_category_id(type_id)
    category_name = resolve_category_id_to_category_name(category_id)
    if not category_name:
        logger.error("Failed to resolve type_id(%s) to category name" % type_id)
    return category_name

def resolve_group_id_to_group_name(group_id):
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute(
                "select groupName from invGroups where groupID = %s" % group_id)
            row = str(cursor.fetchone()[0])
        return row
    except ConnectionDoesNotExist as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
        raise(e)
    except OperationalError as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
        raise(e)
    except Exception as e:
        logger.error(
            "Error resolving EVE type_id(%s) to group_id: %s" % (group_id, e))

    logger.warning("Resolving group_id using ESI")
    group_name = get_group_id(group_id)['name']
    if not group_name:
        logger.error("Error resolving EVE type_id(%s) to group_id" % group_id)
    return group_name 


def resolve_type_id_to_group_name(type_id):
    group_id = resolve_type_id_to_group_id(type_id)
    return resolve_group_id_to_group_name(group_id)


def resolve_group_id_to_category_id(group_id):
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute(
                "select categoryID from invGroups where groupID = %s" % group_id)
            row = str(cursor.fetchone()[0])
        return row
    except ConnectionDoesNotExist as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
        raise(e)
    except OperationalError as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
        raise(e)
    except Exception as e:
        logger.error(
            "Error resolving EVE group_id(%s) to category_id: %s" % (group_id, e))
    logger.warning("Resolving category_id using ESI")
    return get_group_id(group_id)['category_id']

def resolve_category_id_to_category_name(category_id):
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute(
                "select categoryName from invCategories where categoryID = %s" % category_id)
            row = str(cursor.fetchone()[0])
        return row
    except ConnectionDoesNotExist as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
        raise(e)
    except OperationalError as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
        raise(e)
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
    try:
        with connections['eve_static'].cursor() as cursor:
            query = "select stationName from staStations where stationID = %s" % location_id
            cursor.execute(query)
            row = str(cursor.fetchone()[0])
        return row
    except TypeError as e:
        logger.info(
            "Unable to find location_id(%s) in static database" % location_id)
    except ConnectionDoesNotExist as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
    except OperationalError as e:
        logger.warning(
            "EVE static database is not installed: this slows down your tasks")
    except Exception as e:
        logger.exception(e)

    logger.warning("Resolving location_id using ESI")
    response = get_station_id(location_id)
    if 'name' not in response:
        return None 
    return response['name']

def resolve_location_from_location_id_location_type(location_id, location_type, token_entity_id):
    location = "Unknown Location"
    logger.debug("Resolving location_id (%s) of location_type(%s) to location_name" %
        (location_id, location_type))
    try:
        if location_type == 'station':
            location = resolve_location_id_to_station(location_id)
        elif location_type == 'structure': 
            location = get_structure_id(location_id, token_entity_id)
        elif location_type == 'other':
            location = get_structure_id(location_id, token_entity_id)
    except Exception as e:
        logger.error("Failed to resolve location_id (%s) of location_type (%s)" % 
            (location_id, location_type))
        logger.exception(e)

    return location
