from django.db import connections
from django_eveonline_connector.utilities.esi.universe import *
from django.db.utils import ConnectionDoesNotExist, OperationalError
import django.db.utils
import logging

logger = logging.getLogger(__name__)

def query_static_database(query, raise_exception=False):
    """
    Executes the SQL query on the 'eve_static' database.
    If the value is not found, returns None. 
    """
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchone()
        if result:
            return result[0]
    except django.db.utils.DatabaseError as e:
        logger.error("EVE Static Database is not properly configured, or ran into an error.")
        if raise_exception:
            raise(e)
        else:
            logger.exception(e)
        
    return None 

def resolve_type_id_to_type_name(type_id, lazy=False):
    """
    Resolves an EVE Online type_id to type_name, using the static database. 
    Returns None if not found.
    """
    query = "select typeName from invTypes where typeID = %s" % type_id
    type_name = query_static_database(query)
    
    if type_name:
        return type_name 
    

    logger.warning("Resolving type_id (%s) using ESI" % type_id)
    type_name = get_type_id(type_id)

    if not type_name:
        logger.error("Failed to resolve type_id (%s) to type_name" % type_id)
        if lazy:
            return "Unknown Type Name"

    return type_name

def resolve_type_name_to_type_id(type_name, lazy=False):
    """
    Resolve type_name to type_id.
    WARNING: Prone to SQL injection, do not expose to user.
    """
    query = "select typeID from invTypes where typeName = '%s'" % type_name
    type_id = query_static_database(query)

    if type_id:
        return type_id         

    logger.warning("Resolving type_id from type_name (%s) using ESI" % type_name)
    response = resolve_names(type_name)
    if 'inventory_types' in response and response['inventory_types'] and 'id' in response['inventory_types'][0]:
        type_id = response['inventory_types'][0]['id']
    
    if not type_id:
        logger.error(
            "Error resolving EVE type_name(%s) to type_id" % type_name)
        if lazy:
            return -1

    return type_id 

def resolve_type_id_to_group_id(type_id, lazy=False):
    query = "select groupID from invTypes where typeID = %s" % type_id
    group_id = query_static_database(query)
    
    if group_id:
        return group_id 

    logger.warning("Resolving group_id from type_id (%s) using ESI" % type_id)

    response = get_type_id(type_id)
    if 'group_type' in response:
        group_id = response['group_id']

    if not group_id:
        logger.error("Error resolving EVE type_id(%s) to group_id" % type_id)
        if lazy:
            return -1

    return group_id 

def resolve_type_id_to_category_name(type_id, lazy=False):
    category_id = resolve_type_id_to_category_id(type_id)
    category_name = resolve_category_id_to_category_name(category_id)
    if not category_name:
        logger.error("Failed to resolve type_id(%s) to category name" % type_id)
        if lazy:
            return "Unknown Category"
    return category_name

def resolve_group_id_to_group_name(group_id, lazy=False):
    query = "select groupName from invGroups where groupID = %s" % group_id
    group_name = query_static_database(query)

    if group_name:
        return group_name

    logger.warning("Resolving group_name from group_id (%s) using ESI" % group_id)
    response = get_group_id(group_id)
    if 'name' in response:
        group_name = response['name']

    if not group_name:
        logger.error("Error resolving EVE type_id(%s) to group_id" % group_id)
        if lazy:
            return "Unknown Group"

    return group_name 


def resolve_type_id_to_group_name(type_id, lazy=False):
    group_id = resolve_type_id_to_group_id(type_id)
    return resolve_group_id_to_group_name(group_id)


def resolve_group_id_to_category_id(group_id, lazy=False):
    query = "select categoryID from invGroups where groupID = %s" % group_id
    category_id = query_static_database(query)

    if category_id:
        return category_id

    logger.warning("Resolving category_id from group_id (%s) using ESI" % group_id)

    response = get_group_id(group_id)
    if 'category_id' in response:
        category_id = response['category_id']
    
    if not category_id:
        logger.error("Error resolving category_id from group_id (%s)" % group_id)
        if lazy:
            return "Unknown Category"
    
    return category_id

def resolve_category_id_to_category_name(category_id, lazy=False):
    query = "select categoryName from invCategories where categoryID = %s" % category_id
    category_name = query_static_database(query)

    if category_name:
        return category_name 

    logger.warning("Resolving category_name from category_id (%s) using ESI" % category_id)
    
    response = get_category_id(category_id)
    if 'name' in response:
        category_name = response['name']

    if not category_name:
        logger.error("Error resolving category_name from category_id (%s)" % category_id)
        if lazy:
            return -1
    return category_name

def resolve_type_id_to_category_id(type_id):
    group_id = resolve_type_id_to_group_id(type_id)
    category_id = resolve_group_id_to_category_id(group_id)
    return int(category_id)


def resolve_location_id_to_station(location_id, lazy=False):
    query = "select stationName from staStations where stationID = %s" % location_id
    station_name = query_static_database(query)

    if station_name:
        return station_name

    if str(location_id) in cache:
        return cache.get(str(location_id))

    logger.warning(
        "Resolving location_id (%s) to station using ESI" % location_id)
    response = get_station_id(location_id)

    if 'name' in response:
        station_name = response['name']
        cache.set(str(location_id), station_name)

    if not station_name:
        if lazy:
            return "Unknown Station"
    
    return station_name 

def resolve_location_id(location_id, token_entity_id):
    location_name = resolve_location_id_to_station(location_id)
    if location_name:
        return location_name

    location_name = get_structure_id(location_id, token_entity_id)
    if location_name:
        return location_name

    return "Unknown Location"
    
def resolve_location_from_location_id_location_type(location_id, location_type, token_entity_id):
    location = f"Unknown Location ({location_id})"
    logger.debug("Resolving location_id (%s) of location_type(%s) to location_name" %
        (location_id, location_type))
    try:
        if location_type == 'station':
            location = resolve_location_id_to_station(location_id)
        elif location_type == 'item': 
            location = get_structure_id(location_id, token_entity_id)
        elif location_type == 'other':
            location = get_structure_id(location_id, token_entity_id)
    except Exception as e:
        logger.error("Failed to resolve location_id (%s) of location_type (%s)" % 
            (location_id, location_type))
        logger.exception(e)

    return location
