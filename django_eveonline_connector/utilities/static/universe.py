from django.db import connections
from django_eveonline_connector.utilities.esi.universe import *
from django_eveonline_connector.exceptions import EveDataResolutionError
from django.db.utils import ConnectionDoesNotExist, OperationalError
import django.db.utils
import logging

logger = logging.getLogger(__name__)

def query_static_database(query, raise_exception=False, fetchall=False):
    """
    Executes the SQL query on the 'eve_static' database.
    If the value is not found, returns None. 
    """
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute(query)
            if fetchall:
                result = cursor.fetchall()
            else:
                result = cursor.fetchone()
        if result:
            if fetchall:
                return result
            return result[0]
    except django.db.utils.DatabaseError as e:
        logger.error("EVE Static Database is not properly configured, or ran into an error.")
        if raise_exception:
            raise(e)
        else:
            logger.exception(e)
        
    return None 

def resolve_type_id_to_type_name(type_id, raise_exception=True):
    """
    Resolves an EVE Online type_id to type_name. Falls back to ESI if not found in static database.

    Returns None if not found.
    """
    query = "select typeName from invTypes where typeID = %s" % type_id
    type_name = query_static_database(query)
    
    if type_name:
        return type_name 
    

    logger.info("Resolving type_id (%s) using ESI" % type_id)
    type_name = get_type_id(type_id)

    if (not type_name or 'name' not in type_name) and raise_exception:
        raise EveDataResolutionError(f"Failed to resolve type_id ({type_id}) to type_name")

    return type_name['name']

def resolve_type_name_to_type_id(type_name, raise_exception=True):
    """
    Resolve type_name to type_id.
    WARNING: Prone to SQL injection, do not expose to user.
    """
    type_name = type_name.replace("'", "''").rstrip()
    query = "select typeID from invTypes where typeName = '%s'" % type_name
    type_id = query_static_database(query)

    if type_id:
        return type_id         

    logger.info("Resolving type_id from type_name (%s) using ESI" % type_name)
    response = resolve_names(type_name)
    if 'inventory_types' in response and response['inventory_types'] and 'id' in response['inventory_types'][0]:
        type_id = response['inventory_types'][0]['id']
    
    if not type_id and raise_exception:
        raise EveDataResolutionError(f"Error resolving EVE type_name({type_name}) to type_id")

    return type_id 

def resolve_type_id_to_group_id(type_id, raise_exception=True):
    query = "select groupID from invTypes where typeID = %s" % type_id
    group_id = query_static_database(query)
    
    if group_id:
        return group_id 

    logger.info("Resolving group_id from type_id (%s) using ESI" % type_id)

    response = get_type_id(type_id)
    if 'group_id' in response:
        group_id = response['group_id']

    if not group_id and raise_exception:
        raise EveDataResolutionError(
            f"Error resolving EVE type_id({type_id}) to group_id")

    return group_id 


def resolve_type_id_to_category_name(type_id, raise_exception=True):
    category_id = resolve_type_id_to_category_id(type_id)
    category_name = resolve_category_id_to_category_name(category_id)
    if not category_name and raise_exception:
        raise EveDataResolutionError(
            f"Failed to resolve type_id({type_id}) to category name")
    return category_name

def resolve_group_id_to_group_name(group_id, raise_exception=True):
    query = "select groupName from invGroups where groupID = %s" % group_id
    group_name = query_static_database(query)

    if group_name:
        return group_name

    logger.info("Resolving group_name from group_id (%s) using ESI" % group_id)
    response = get_group_id(group_id)
    if 'name' in response:
        group_name = response['name']

    if not group_name and raise_exception:
        raise EveDataResolutionError(
            f"Error resolving EVE type_id({group_id}) to group_id")

    return group_name 


def resolve_type_id_to_group_name(type_id):
    group_id = resolve_type_id_to_group_id(type_id)
    return resolve_group_id_to_group_name(group_id)


def resolve_group_id_to_category_id(group_id, raise_exception=True):
    query = "select categoryID from invGroups where groupID = %s" % group_id
    category_id = query_static_database(query)

    if category_id:
        return category_id

    logger.info("Resolving category_id from group_id (%s) using ESI" % group_id)

    response = get_group_id(group_id)
    if 'category_id' in response:
        category_id = response['category_id']
    
    if not category_id and raise_exception:
        raise EveDataResolutionError(
            f"Error resolving category_id from group_id ({group_id})")
    
    return category_id

def resolve_category_id_to_category_name(category_id, raise_exception=True):
    query = "select categoryName from invCategories where categoryID = %s" % category_id
    category_name = query_static_database(query)

    if category_name:
        return category_name 

    logger.info("Resolving category_name from category_id (%s) using ESI" % category_id)
    
    response = get_category_id(category_id)
    if 'name' in response:
        category_name = response['name']

    if not category_name and raise_exception:
        raise EveDataResolutionError(
            f"Error resolving category_name from category_id ({category_id})")

    return category_name

def resolve_type_id_to_category_id(type_id):
    group_id = resolve_type_id_to_group_id(type_id)
    category_id = resolve_group_id_to_category_id(group_id)
    return int(category_id)


def resolve_location_id_to_station(location_id, raise_exception=True):
    if location_id < 60000000 or location_id > 64000000:
        raise EveDataResolutionError('Attempted to resolve a station outside of the possible range')
    
    query = "select stationName from staStations where stationID = %s" % location_id
    station_name = query_static_database(query)

    if station_name:
        return station_name

    if str(location_id) in cache:
        return cache.get(str(location_id))

    logger.info(
        "Resolving location_id (%s) to station using ESI" % location_id)
    response = get_station_id(location_id)

    if 'name' in response:
        station_name = response['name']
        cache.set(str(location_id), station_name)

    if not station_name and raise_exception:
        raise EveDataResolutionError(f"Failed to resolve location_id({location_id} to station")
    elif not station_name:
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
        else:
            location = get_structure_id(location_id, token_entity_id)
            
    except Exception as e:
        raise EveDataResolutionError(
            f"Failed to resolve location_id ({location_id}) of location_type ({location_type}). Reason: {str(e)}")

    return location

def get_type_id_prerq_skill_ids(type_id):
    query = """SELECT 
        i.typeID         as itemID, 
        ip.typeID        as prerqSkillID,
        dtal.valueInt    as prerqSkillLevelInt,
        dtal.valueFloat  as prerqSkillLevelFloat
    FROM invGroups g
    LEFT JOIN invTypes i 
        ON i.groupID = g.groupID
    LEFT JOIN dgmTypeAttributes dta
        ON dta.typeID = i.typeID AND
            dta.attributeID IN (182, 183, 184, 1285, 1289, 1290)
    LEFT JOIN dgmTypeAttributes dtal 
        ON dtal.typeID = dta.typeID AND 
        (
            (dtal.attributeID = 277 AND dta.attributeID = 182) OR
            (dtal.attributeID = 278 AND dta.attributeID = 183) OR
            (dtal.attributeID = 279 AND dta.attributeID = 184) OR
            (dtal.attributeID = 1286 AND dta.attributeID = 1285) OR
            (dtal.attributeID = 1287 AND dta.attributeID = 1289) OR
            (dtal.attributeID = 1288 AND dta.attributeID = 1290)
        )
    JOIN invTypes ip 
        ON ip.typeID = dta.valueInt OR
            ip.typeID = dta.valueFloat

    WHERE i.typeID=%s
        AND i.published = 1
        AND g.categoryID NOT IN (0,1,2,3,25)
    ORDER BY g.groupName DESC
    """ % str(type_id)

    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()
    except django.db.utils.DatabaseError as e:
        raise EveDataResolutionError(
            f"EVE Static Database is not properly configured, or ran into an error. {e}")
    return result


def get_prerequisite_skills(type_id):
    skill_to_resolve = type_id.pop(0)
    prereqs = get_type_id_prerq_skill_ids(skill_to_resolve[1])
    skill_to_save = { 
        'name': resolve_type_id_to_type_name(skill_to_resolve[1]),
        'type_id': skill_to_resolve[1],
        'level': skill_to_resolve[3],
    }
    if prereqs or type_id:
        return [skill_to_save] + get_prerequisite_skills(type_id + prereqs)
    else:
        return [skill_to_save]
