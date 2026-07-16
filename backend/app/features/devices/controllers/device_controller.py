from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.features.devices.schemas.device import DeviceCreate, DeviceUpdate
from app.features.devices.services.device_service_interface import IDeviceService
from app.features.devices.errors.device import DeviceAlreadyExistsError, DeviceNotFoundError
from app.shared.logging_context import structured_extra
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


def create_device_controller(data: DeviceCreate, db: Session, service: IDeviceService):
    try:
        return service.create_device(data, db)
    except DeviceAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception(
            "Device create failed",
            extra=structured_extra("device_create_failed"),
        )
        raise HTTPException(status_code=400, detail=str(e))


def get_devices_controller(db: Session, service: IDeviceService):
    try:
        return service.get_devices(db)
    except Exception:
        logger.exception(
            "Device list failed",
            extra=structured_extra("device_list_failed"),
        )
        raise HTTPException(status_code=500, detail="Failed to fetch devices")


def update_device_controller(device_id: int, data: DeviceUpdate, db: Session, service: IDeviceService):
    try:
        return service.update_device(device_id, data, db)
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DeviceAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception(
            "Device update failed",
            extra=structured_extra("device_update_failed", device_id=device_id),
        )
        raise HTTPException(status_code=400, detail=str(e))


def delete_device_controller(device_id: int, db: Session, service: IDeviceService):
    try:
        return service.delete_device(device_id, db)
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception(
            "Device delete failed",
            extra=structured_extra("device_delete_failed", device_id=device_id),
        )
        raise HTTPException(status_code=500, detail="Failed to delete device")
