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
    def mark_processed(ps_id, actual_quantity=None):
        suggestion = PurchaseSuggestionRepository.get_by_id(ps_id)
        if not suggestion:
            return False, "采购建议不存在"
        if suggestion['status'] != 'PENDING':
            status_map = {'PROCESSED': '已处理', 'IGNORED': '已忽略'}
            return False, f"该采购建议已{status_map.get(suggestion['status'], suggestion['status'])}，无需重复处理"

        part = PartRepository.get_by_id(suggestion['part_id'])
        if not part:
            return False, "关联配件不存在"

        qty = actual_quantity if actual_quantity is not None else suggestion['suggested_quantity']
        if qty <= 0:
            return False, "采购数量必须大于0"

        ok, err = PartService.stock_in(part['id'], qty, note=f'按采购建议#{ps_id}采购入库')
        if not ok:
            return False, f"入库失败: {err}"

        PurchaseSuggestionRepository.update_status(ps_id, 'PROCESSED')
        return True, {
            'part_name': part['name'],
            'part_code': part['code'],
            'purchased_qty': qty,
            'new_stock': part['stock'] + qty
        }

    @staticmethod
    def mark_ignored(ps_id):
        PurchaseSuggestionRepository.update_status(ps_id, 'IGNORED')

    @staticmethod
    def batch_process_suggestions(ps_ids_with_qty=None):
        ps_ids_with_qty = ps_ids_with_qty or []
        results = []
        for item in ps_ids_with_qty:
            ps_id = item['id']
            qty = item.get('quantity')
            ok, res = PurchaseSuggestionService.mark_processed(ps_id, qty)
            results.append({'id': ps_id, 'success': ok, 'result': res})
        return results

    @staticmethod
    def get_suggestion_statistics():
        all_suggestions = PurchaseSuggestionRepository.get_all()
        pending = [s for s in all_suggestions if s['status'] == 'PENDING']
        processed = [s for s in all_suggestions if s['status'] == 'PROCESSED']
        ignored = [s for s in all_suggestions if s['status'] == 'IGNORED']

        total_pending_qty = sum(s['suggested_quantity'] for s in pending)
        total_processed_qty = sum(s['suggested_quantity'] for s in processed)

        low_parts = PartService.get_low_stock_parts()
        low_stock_value = sum(p['price'] * p['stock'] for p in low_parts)
        total_suggested_value = 0.0
        for s in pending:
            part = PartService.find_part_by_id(s['part_id'])
            if part:
                total_suggested_value += part['price'] * s['suggested_quantity']

        return {
            'total': len(all_suggestions),
            'pending_count': len(pending),
            'processed_count': len(processed),
            'ignored_count': len(ignored),
            'pending_parts_count': len(low_parts),
            'total_pending_qty': total_pending_qty,
            'total_processed_qty': total_processed_qty,
            'total_suggested_value': round(total_suggested_value, 2),
            'pending_suggestions': pending,
            'low_stock_parts': low_parts
        }


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
    def get_vehicle_history(plate_number, include_void=False):
        vehicle = VehicleRepository.get_by_plate(plate_number)
        if not vehicle:
            return None
        orders = WorkOrderRepository.get_by_vehicle_id(vehicle['id'])
        if not include_void:
            orders = [o for o in orders if o.get('status') != 'VOID']
        for o in orders:
            o['parts'] = WorkOrderPartRepository.get_by_work_order_id(o['id'])
        return {
            'vehicle': vehicle,
            'orders': orders
        }

    @staticmethod
    def get_vehicle_overview(plate_number):
        vehicle = VehicleRepository.get_by_plate(plate_number)
        if not vehicle:
            return None, "未找到该车辆"

        orders = WorkOrderRepository.get_by_vehicle_id(vehicle['id'])
        normal_orders = [o for o in orders if o.get('status') != 'VOID']
        normal_orders_sorted = sorted(
            normal_orders,
            key=lambda x: (x['created_at'], x['id']),
            reverse=True
        )

        total_cost = sum(o['total_cost'] for o in normal_orders)
        order_count = len(normal_orders)

        latest_mileage = vehicle['last_maintenance_mileage']
        if normal_orders_sorted:
            latest_mileage = normal_orders_sorted[0]['mileage']

        mileage_diff = latest_mileage - vehicle['last_maintenance_mileage']
        maintenance_due = mileage_diff >= MAINTENANCE_INTERVAL
        maintenance_remaining = MAINTENANCE_INTERVAL - mileage_diff

        recent_orders = normal_orders_sorted[:5]
        for o in recent_orders:
            o['parts'] = WorkOrderPartRepository.get_by_work_order_id(o['id'])

        void_count = len([o for o in orders if o.get('status') == 'VOID'])

        return True, {
            'vehicle': vehicle,
            'total_spent': round(total_cost, 2),
            'order_count': order_count,
            'void_count': void_count,
            'latest_mileage': latest_mileage,
            'mileage_since_maintenance': mileage_diff,
            'maintenance_due': maintenance_due,
            'maintenance_remaining': max(maintenance_remaining, 0),
            'recent_orders': recent_orders
        }

    @staticmethod
    def get_revenue_statistics(start_date, end_date):
        orders = WorkOrderRepository.get_by_date_range(start_date, end_date)
        orders = [o for o in orders if o.get('status') != 'VOID']
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
        ok, err = WorkOrderRepository.delete(order_id)
        return ok, err

    @staticmethod
    def cancel_work_order(order_id):
        order = WorkOrderRepository.get_by_id(order_id)
        if not order:
            return False, "工单不存在"
        if order.get('status') == 'VOID':
            return False, "工单已被撤销，请勿重复操作"

        parts = WorkOrderPartRepository.get_by_work_order_id(order_id)
        for p in parts:
            part = PartRepository.get_by_id(p['part_id'])
            if not part:
                continue
            new_stock = part['stock'] + p['quantity']
            PartRepository.update_stock(p['part_id'], new_stock)
            PartTransactionRepository.create(
                p['part_id'], p['quantity'], 'IN',
                order_id=order_id, note=f'撤销工单#{order_id}回退库存'
            )

        WorkOrderRepository.update_status(order_id, 'VOID')
        return True, {
            'parts_count': len(parts),
            'refund_amount': order['total_cost'],
            'returned_stock': sum(p['quantity'] for p in parts)
        }

    @staticmethod
    def resettle_work_order(order_id, new_fault_description=None,
                            new_fault_code_id=None, new_labor_cost=None,
                            new_parts=None):
        order = WorkOrderRepository.get_by_id(order_id)
        if not order:
            return False, "工单不存在"
        if order.get('status') == 'VOID':
            return False, "已撤销的工单无法重新结算"

        old_parts = WorkOrderPartRepository.get_by_work_order_id(order_id)
        for p in old_parts:
            part = PartRepository.get_by_id(p['part_id'])
            if part:
                new_stock = part['stock'] + p['quantity']
                PartRepository.update_stock(p['part_id'], new_stock)
                PartTransactionRepository.create(
                    p['part_id'], p['quantity'], 'IN',
                    order_id=order_id, note=f'重新结算回退库存'
                )

        WorkOrderPartRepository.delete_by_work_order_id(order_id)

        new_parts = new_parts or []
        merged_parts = {}
        for p in new_parts:
            pid = p['part_id']
            if pid in merged_parts:
                merged_parts[pid]['quantity'] += p['quantity']
            else:
                merged_parts[pid] = {'part_id': pid, 'quantity': p['quantity']}
        new_parts = list(merged_parts.values())

        parts_total = 0.0
        valid_parts = []
        for p in new_parts:
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

        labor_cost = new_labor_cost if new_labor_cost is not None else order['labor_cost']
        total_cost = parts_total + float(labor_cost)

        updates = {
            'labor_cost': labor_cost,
            'total_cost': total_cost,
            'status': 'NORMAL'
        }
        if new_fault_description is not None:
            updates['fault_description'] = new_fault_description
        if new_fault_code_id is not None:
            updates['fault_code_id'] = new_fault_code_id

        WorkOrderRepository.update_full(order_id, **updates)

        for vp in valid_parts:
            WorkOrderPartRepository.create(
                order_id, vp['part_id'], vp['part_name'], vp['part_code'],
                vp['unit_price'], vp['quantity'], vp['subtotal']
            )
            PartService.stock_out(vp['part_id'], vp['quantity'], order_id=order_id)

        return True, {
            'order_id': order_id,
            'old_total': order['total_cost'],
            'new_total': total_cost,
            'diff': round(total_cost - order['total_cost'], 2),
            'parts_count': len(valid_parts)
        }
