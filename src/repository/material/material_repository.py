from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from src.core.utils.model_filter import apply_dynamic_filters
from src.database.base import BaseRepository
from src.repository import Material
from src.schemas.base import RequestAllObject
from src.schemas.material.create import MaterialCreateSchema
from src.schemas.material.update import MaterialUpdateSchema

class MaterialRepository(BaseRepository[Material]):
    async def create(self, material: Material) -> Material:
        self.db.add(material)
        await self.db.flush()
        await self.db.refresh(material)
        return material
    
    async def get_by_ids(self, ids: list[int], lock: bool = False) -> list[Material]:
        stmt = select(Material).where(Material.id.in_(ids))
        if lock: stmt = stmt.order_by(Material.id).with_for_update()
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_all(self, data: RequestAllObject) -> tuple[list[Material], int]:
        count_stmt = select(func.count()).select_from(Material)
        stmt = select(Material)
        count_stmt = apply_dynamic_filters(count_stmt, Material, data.filters)
        stmt = apply_dynamic_filters(stmt, Material, data.filters)
        total_items = await self.db.scalar(count_stmt) or 0
        offset_value = (data.page - 1) * data.pageSize
        stmt = stmt.order_by(Material.id.asc()).offset(offset_value).limit(data.pageSize)
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        return items, total_items