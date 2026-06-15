from repository import (
    VehicleRepository, PartRepository, PartTransactionRepository,
    FaultCodeRepository, WorkOrderRepository, WorkOrderPartRepository,
    PurchaseSuggestionRepository
)
from database import MAINTENANCE_INTERVAL
from datetime import datetime


class VehicleService:
    @staticmethod
    def add_vehicle(plate_number, brand_model, vin_code, last_maintenance_mileage=0):
        existing_plate = VehicleRepository.get_by_plate(plate_number)
        if existing_plate:
            return None, f"车牌号 {plate_number} 已存在，请检查后重新输入"
        existing_vin = VehicleRepository.get_by_vin(vin_code)
        if existing_vin:
            return None, f"VIN码 {vin_code} 已被车辆 [{existing_vin['plate_number']}] 使用，请检查后重新输入"
        vehicle_id = VehicleRepository.create(plate_number, brand_model, vin_code, last_maintenance_mileage)
        return vehicle_id, None

    @staticmethod
    def find_vehicle_by_vin(vin_code):
        return VehicleRepository.get_by_vin(vin_code)

    @staticmethod
    def list_vehicles():
        return VehicleRepository.get_all()

    @staticmethod
    def find_vehicle_by_plate(plate_number):
        return VehicleRepository.get_by_plate(plate_number)

    @staticmethod
    def find_vehicle_by_id(vehicle_id):
        return VehicleRepository.get_by_id(vehicle_id)

    @staticmethod
    def update_vehicle(vehicle_id, **kwargs):
        VehicleRepository.update(vehicle_id, **kwargs)

    @staticmethod
    def delete_vehicle(vehicle_id, cascade=False):
        order_count = VehicleRepository.get_work_order_count(vehicle_id)
        if order_count > 0 and not cascade:
            return False, f"该车辆存在 {order_count} 条维修记录，无法直接删除。如需删除请选择级联删除（将同时删除所有关联工单）"
        ok, err = VehicleRepository.delete(vehicle_id)
        if not ok:
            return False, err
        return True, None

    @staticmethod
    def get_work_order_count(vehicle_id):
        return VehicleRepository.get_work_order_count(vehicle_id)

    @staticmethod
    def check_maintenance_due(vehicle_id, current_mileage):
        vehicle = VehicleRepository.get_by_id(vehicle_id)
        if not vehicle:
            return False, 0
        last_mileage = vehicle['last_maintenance_mileage'] or 0
        diff = current_mileage - last_mileage
        return diff >= MAINTENANCE_INTERVAL, diff


class PartService:
    @staticmethod
    def add_part(name, code, price, stock=0, min_stock=5):
        existing = PartRepository.get_by_code(code)
        if existing:
            return None, f"配件编号 {code} 已存在"
        part_id = PartRepository.create(name, code, price, stock, min_stock)
        if stock > 0:
            PartTransactionRepository.create(part_id, stock, 'IN', note='初始入库')
        return part_id, None

    @staticmethod
    def list_parts():
        return PartRepository.get_all()

    @staticmethod
    def find_part_by_id(part_id):
        return PartRepository.get_by_id(part_id)

    @staticmethod
    def find_part_by_code(code):
        return PartRepository.get_by_code(code)

    @staticmethod
    def search_parts(keyword):
        return PartRepository.search(keyword)

    @staticmethod
    def update_part(part_id, **kwargs):
        PartRepository.update(part_id, **kwargs)

    @staticmethod
    def delete_part(part_id):
        PartRepository.delete(part_id)

    @staticmethod
    def stock_in(part_id, quantity, note=None):
        part = PartRepository.get_by_id(part_id)
        if not part:
            return False, "配件不存在"
        new_stock = part['stock'] + quantity
        PartRepository.update_stock(part_id, new_stock)
        PartTransactionRepository.create(part_id, quantity, 'IN', note=note or '采购入库')
        return True, None

    @staticmethod
    def stock_out(part_id, quantity, order_id=None, note=None):
        part = PartRepository.get_by_id(part_id)
        if not part:
            return False, "配件不存在"
        if part['stock'] < quantity:
            return False, f"库存不足，当前库存：{part['stock']}"
        new_stock = part['stock'] - quantity
        PartRepository.update_stock(part_id, new_stock)
        PartTransactionRepository.create(part_id, quantity, 'OUT', order_id=order_id, note=note or '维修领用')
        if new_stock < part['min_stock']:
            PurchaseSuggestionService.check_and_create(part_id)
        return True, None

    @staticmethod
    def get_low_stock_parts():
        return PartRepository.get_low_stock()

    @staticmethod
    def list_transactions(start_date=None, end_date=None, part_id=None):
        if start_date and end_date:
            return PartTransactionRepository.get_by_date_range(start_date, end_date)
        if part_id:
            return PartTransactionRepository.get_by_part_id(part_id)
        return PartTransactionRepository.get_all()


class PurchaseSuggestionService:
    @staticmethod
    def check_and_create(part_id):
        if PurchaseSuggestionRepository.exists_pending_for_part(part_id):
            return
        part = PartRepository.get_by_id(part_id)
        if not part:
            return
        if part['stock'] >= part['min_stock']:
            return
        suggested = part['min_stock'] * 2 - part['stock']
        if suggested < 1:
            suggested = 1
        PurchaseSuggestionRepository.create(part['id'], part['name'], part['stock'], suggested)

    @staticmethod
    def generate_all_suggestions():
        low_stock_parts = PartRepository.get_low_stock()
        for part in low_stock_parts:
            PurchaseSuggestionService.check_and_create(part['id'])
        return PurchaseSuggestionRepository.get_pending()

    @staticmethod
    def list_suggestions(status=None):
        return PurchaseSuggestionRepository.get_all(status)

    @staticmethod
    def mark_processed(ps_id):
        PurchaseSuggestionRepository.update_status(ps_id, 'PROCESSED')

    @staticmethod
    def mark_ignored(ps_id):
        PurchaseSuggestionRepository.update_status(ps_id, 'IGNORED')


class FaultCodeService:
    @staticmethod
    def add_fault_code(code, description, solution):
        existing = FaultCodeRepository.get_by_code(code)
        if existing:
            return None, f"故障码 {code} 已存在"
        fc_id = FaultCodeRepository.create(code, description, solution)
        return fc_id, None

    @staticmethod
    def list_fault_codes():
        return FaultCodeRepository.get_all()

    @staticmethod
    def find_by_code(code):
        return FaultCodeRepository.get_by_code(code)

    @staticmethod
    def find_by_id(fc_id):
        return FaultCodeRepository.get_by_id(fc_id)

    @staticmethod
    def search_fault_codes(keyword):
        return FaultCodeRepository.search(keyword)

    @staticmethod
    def update_fault_code(fc_id, **kwargs):
        FaultCodeRepository.update(fc_id, **kwargs)

    @staticmethod
    def delete_fault_code(fc_id):
        FaultCodeRepository.delete(fc_id)


class WorkOrderService:
    @staticmethod
    def create_work_order(vehicle_id, mileage, fault_description, fault_code_id=None,
                          labor_cost=0, parts=None):
        parts = parts or []

        merged_parts = {}
        for p in parts:
            pid = p['part_id']
            if pid in merged_parts:
                merged_parts[pid]['quantity'] += p['quantity']
            else:
                merged_parts[pid] = {'part_id': pid, 'quantity': p['quantity']}
        parts = list(merged_parts.values())

        parts_total = 0.0
        valid_parts = []

        for p in parts:
            part = PartRepository.get_by_id(p['part_id'])
            if not part:
                continue
            if part['stock'] < p['quantity']:
                continue
            subtotal = part['price'] * p['quantity']
            parts_total += subtotal
            valid_parts.append({
                'part_id': part['id'],
                'part_name': part['name'],
                'part_code': part['code'],
                'unit_price': part['price'],
                'quantity': p['quantity'],
                'subtotal': subtotal
            })

        total_cost = parts_total + float(labor_cost)

        order_id = WorkOrderRepository.create(
            vehicle_id, mileage, fault_description, fault_code_id, labor_cost, total_cost
        )

        for vp in valid_parts:
            WorkOrderPartRepository.create(
                order_id, vp['part_id'], vp['part_name'], vp['part_code'],
                vp['unit_price'], vp['quantity'], vp['subtotal']
            )
            PartService.stock_out(vp['part_id'], vp['quantity'], order_id=order_id)

        maintenance_due, mileage_diff = VehicleService.check_maintenance_due(vehicle_id, mileage)

        return {
            'order_id': order_id,
            'total_cost': total_cost,
            'parts_count': len(valid_parts),
            'maintenance_due': maintenance_due,
            'mileage_since_last': mileage_diff
        }

    @staticmethod
    def list_work_orders(start_date=None, end_date=None, vehicle_id=None):
        if start_date and end_date:
            return WorkOrderRepository.get_by_date_range(start_date, end_date)
        if vehicle_id:
            return WorkOrderRepository.get_by_vehicle_id(vehicle_id)
        return WorkOrderRepository.get_all()

    @staticmethod
    def get_work_order_detail(order_id):
        order = WorkOrderRepository.get_by_id(order_id)
        if not order:
            return None
        parts = WorkOrderPartRepository.get_by_work_order_id(order_id)
        order['parts'] = parts
        return order

    @staticmethod
    def get_vehicle_history(plate_number):
        vehicle = VehicleRepository.get_by_plate(plate_number)
        if not vehicle:
            return None
        orders = WorkOrderRepository.get_by_vehicle_id(vehicle['id'])
        for o in orders:
            o['parts'] = WorkOrderPartRepository.get_by_work_order_id(o['id'])
        return {
            'vehicle': vehicle,
            'orders': orders
        }

    @staticmethod
    def get_revenue_statistics(start_date, end_date):
        orders = WorkOrderRepository.get_by_date_range(start_date, end_date)
        total_revenue = 0.0
        total_labor = 0.0
        total_parts_cost = 0.0
        order_count = len(orders)

        for o in orders:
            total_revenue += o['total_cost']
            total_labor += o['labor_cost']
            parts = WorkOrderPartRepository.get_by_work_order_id(o['id'])
            for p in parts:
                total_parts_cost += p['subtotal']

        return {
            'start_date': start_date,
            'end_date': end_date,
            'order_count': order_count,
            'total_revenue': round(total_revenue, 2),
            'total_labor': round(total_labor, 2),
            'total_parts_cost': round(total_parts_cost, 2),
            'avg_order_value': round(total_revenue / order_count, 2) if order_count > 0 else 0.0,
            'orders': orders
        }

    @staticmethod
    def delete_work_order(order_id):
        WorkOrderPartRepository.delete_by_work_order_id(order_id)
        WorkOrderRepository.delete(order_id)
