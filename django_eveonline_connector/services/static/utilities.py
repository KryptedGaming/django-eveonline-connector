from django.db import connections
import logging

logger = logging.getLogger(__name__)

def resolve_type_id_to_type_name(type_id):
    from django.db.utils import ConnectionDoesNotExist
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute("select typeName from invTypes where typeID = %s" % type_id)
            row = str(cursor.fetchone()[0])
        return row
    except ConnectionDoesNotExist as e:
        logger.error("EVE static database needs to be installed")
        return "err_no_static_database"
    except Exception as e:
        logger.error("Error resolving EVE type_id(%s) to type_name: %s" % (type_id, e))
    return "Unknown"

def resolve_type_id_to_group_id(type_id):
    from django.db.utils import ConnectionDoesNotExist
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute("select groupID from invTypes where typeID = %s" % type_id)
            row = str(cursor.fetchone()[0])
        return row
    except ConnectionDoesNotExist as e:
        logger.error("EVE static database needs to be installed")
        return "err_no_static_database"
    except Exception as e:
        logger.error("Error resolving EVE type_id(%s) to group_id: %s" % (type_id, e))
    return 0

def resolve_group_id_to_category_id(group_id):
    from django.db.utils import ConnectionDoesNotExist
    try:
        with connections['eve_static'].cursor() as cursor:
            cursor.execute("select categoryID from invGroups where groupID = %s" % group_id)
            row = str(cursor.fetchone()[0])
        return row
    except ConnectionDoesNotExist as e:
        logger.error("EVE static database needs to be installed")
        return "err_no_static_database"
    except Exception as e:
        logger.error("Error resolving EVE group_id(%s) to category_id: %s" % (group_id, e))
    return 0

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
        logger.error("EVE static database needs to be installed")
        return "err_no_static_database"
    except Exception as e:
        logger.error(e)