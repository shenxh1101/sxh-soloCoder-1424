import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, seed_sample_data, migrate_db, DB_PATH, MAINTENANCE_INTERVAL
from services import (
    VehicleService, PartService, FaultCodeService,
    WorkOrderService, PurchaseSuggestionService
)
from reports import (
    export_parts_list, export_parts_template, import_parts_from_excel,
    export_revenue_report
)


def cleanup():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    for d in ['data', 'exports']:
        if os.path.exists(d):
            import shutil
            shutil.rmtree(d, ignore_errors=True)


def test_delete_vehicle_cascade():
    print("\n" + "=" * 60)
    print("测试 1: 删除车辆时清理所有关联流水(parts_transactions)")
    print("=" * 60)

    try:
        vid, _ = VehicleService.add_vehicle("京T00001", "测试车1", "TVIN0000000000001", 0)
        oil = PartService.find_part_by_code("P001")
        oil_before = oil['stock']

        result = WorkOrderService.create_work_order(
            vid, 5000, "测试保养", None, 50,
            [{'part_id': oil['id'], 'quantity': 2}]
        )
        assert result['order_id'] is not None
        print(f"[✓] 创建带配件工单 #{result['order_id']}")

        txns = PartService.list_transactions(part_id=oil['id'])
        order_txns = [t for t in txns if t['order_id'] == result['order_id']]
        assert len(order_txns) >= 1, "工单关联的配件流水应存在"
        print(f"[✓] 工单关联配件流水存在，共 {len(order_txns)} 条")

        ok, err = VehicleService.delete_vehicle(vid, cascade=True)
        assert ok, f"级联删除失败: {err}"
        print(f"[✓] 级联删除车辆成功")

        v = VehicleService.find_vehicle_by_id(vid)
        assert v is None, "车辆应已删除"
        print(f"[✓] 车辆记录已删除")

        orders = WorkOrderService.list_work_orders(vehicle_id=vid)
        assert len(orders) == 0, "工单应已删除"
        print(f"[✓] 关联工单已删除")

        txns_after = PartService.list_transactions(part_id=oil['id'])
        order_txns_after = [t for t in txns_after if t['order_id'] == result['order_id']]
        assert len(order_txns_after) == 0, "关联流水应已删除"
        print(f"[✓] 关联配件出入库流水已清理")

        oil_after = PartService.find_part_by_code("P001")['stock']
        print(f"  机油库存: {oil_before} -> {oil_after} (扣减2件保持不变，因删除车辆不回滚业务)")
        print("[✓] 测试 1 通过: 删除车辆时所有关联数据完整清理")
        return True
    except Exception as e:
        print(f"[✗] 测试 1 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cancel_work_order():
    print("\n" + "=" * 60)
    print("测试 2: 工单撤销 - 库存/金额/历史全回滚")
    print("=" * 60)

    try:
        vid, _ = VehicleService.add_vehicle("京T00002", "测试车2", "TVIN0000000000002", 10000)
        oil = PartService.find_part_by_code("P001")
        filter_p = PartService.find_part_by_code("P002")
        oil_before = oil['stock']
        filter_before = filter_p['stock']

        result = WorkOrderService.create_work_order(
            vid, 15000, "常规保养", None, 100,
            [{'part_id': oil['id'], 'quantity': 2}, {'part_id': filter_p['id'], 'quantity': 1}]
        )
        oid = result['order_id']
        total_before = result['total_cost']
        print(f"[✓] 创建工单 #{oid}，总金额¥{total_before:.2f}")

        oil_after_create = PartService.find_part_by_code("P001")['stock']
        filter_after_create = PartService.find_part_by_code("P002")['stock']
        assert oil_after_create == oil_before - 2
        assert filter_after_create == filter_before - 1
        print(f"[✓] 工单扣减库存: 机油 {oil_before}->{oil_after_create}, 滤清器 {filter_before}->{filter_after_create}")

        from datetime import datetime, timedelta
        today = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        stats_before = WorkOrderService.get_revenue_statistics(start, today)
        assert stats_before['order_count'] >= 1
        print(f"[✓] 撤销前收入统计: 工单{stats_before['order_count']}个, 收入¥{stats_before['total_revenue']:.2f}")

        ok, res = WorkOrderService.cancel_work_order(oid)
        assert ok, f"撤销失败: {res}"
        print(f"[✓] 工单撤销成功: 返还配件{res['returned_stock']}件, 冲销¥{res['refund_amount']:.2f}")

        oil_after_cancel = PartService.find_part_by_code("P001")['stock']
        filter_after_cancel = PartService.find_part_by_code("P002")['stock']
        assert oil_after_cancel == oil_before, f"机油库存未回滚: {oil_before} vs {oil_after_cancel}"
        assert filter_after_cancel == filter_before, f"滤清器库存未回滚: {filter_before} vs {filter_after_cancel}"
        print(f"[✓] 撤销后库存回滚: 机油->{oil_after_cancel}, 滤清器->{filter_after_cancel}")

        order = WorkOrderService.get_work_order_detail(oid)
        assert order['status'] == 'VOID', f"状态应为VOID: {order['status']}"
        print(f"[✓] 工单状态已标记为: {order['status']}")

        history = WorkOrderService.get_vehicle_history("京T00002")
        void_orders = [o for o in history['orders'] if o.get('status') == 'VOID']
        assert len(void_orders) == 0, "维修历史中不应包含撤销工单"
        print(f"[✓] 维修历史已排除撤销工单")

        stats_after = WorkOrderService.get_revenue_statistics(start, today)
        assert stats_after['total_revenue'] == stats_before['total_revenue'] - total_before, \
            f"收入统计未扣减撤销金额: {stats_before['total_revenue']} - {total_before} != {stats_after['total_revenue']}"
        print(f"[✓] 收入统计已扣减撤销金额: ¥{stats_before['total_revenue']:.2f} -> ¥{stats_after['total_revenue']:.2f}")

        ok2, _ = WorkOrderService.cancel_work_order(oid)
        assert not ok2, "重复撤销应被拦截"
        print(f"[✓] 重复撤销正确拦截")

        print("[✓] 测试 2 通过: 工单撤销全链路回滚正常")
        return True
    except Exception as e:
        print(f"[✗] 测试 2 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_resettle_work_order():
    print("\n" + "=" * 60)
    print("测试 3: 工单重新结算")
    print("=" * 60)

    try:
        vid, _ = VehicleService.add_vehicle("京T00003", "测试车3", "TVIN0000000000003", 20000)
        oil = PartService.find_part_by_code("P001")
        filter_p = PartService.find_part_by_code("P002")
        air = PartService.find_part_by_code("P003")
        oil_before = oil['stock']

        result = WorkOrderService.create_work_order(
            vid, 25000, "初始保养", None, 80,
            [{'part_id': oil['id'], 'quantity': 1}]
        )
        oid = result['order_id']
        old_total = result['total_cost']
        print(f"[✓] 初始工单: 机油x1 + 工时¥80 = ¥{old_total:.2f}")

        ok, res = WorkOrderService.resettle_work_order(
            oid,
            new_fault_description="大保养升级",
            new_fault_code_id=None,
            new_labor_cost=150,
            new_parts=[
                {'part_id': oil['id'], 'quantity': 2},
                {'part_id': filter_p['id'], 'quantity': 1},
                {'part_id': air['id'], 'quantity': 1},
            ]
        )
        assert ok, f"重新结算失败: {res}"
        print(f"[✓] 重新结算: 原¥{res['old_total']:.2f} -> 新¥{res['new_total']:.2f}, 差额¥{res['diff']:.2f}")

        expected_parts_cost = 2 * oil['price'] + 1 * filter_p['price'] + 1 * air['price']
        expected_total = expected_parts_cost + 150
        assert abs(res['new_total'] - expected_total) < 0.01, \
            f"总费用计算错误: {res['new_total']} vs {expected_total}"

        oil_after = PartService.find_part_by_code("P001")['stock']
        assert oil_after == oil_before - 2, f"机油库存应为{oil_before - 2}, 实际{oil_after}"
        print(f"[✓] 库存正确: 机油{oil_before}->{oil_after}(扣2件，原扣1件已退库后扣2件)")

        order = WorkOrderService.get_work_order_detail(oid)
        assert order['fault_description'] == "大保养升级"
        assert len(order['parts']) == 3
        parts_map = {p['part_code']: p['quantity'] for p in order['parts']}
        assert parts_map.get('P001') == 2
        assert parts_map.get('P002') == 1
        assert parts_map.get('P003') == 1
        print(f"[✓] 工单详情已更新: 故障描述+配件(3项)")

        parts_cost_in_detail = sum(p['subtotal'] for p in order['parts'])
        total_in_detail = parts_cost_in_detail + order['labor_cost']
        assert abs(total_in_detail - order['total_cost']) < 0.01
        assert abs(total_in_detail - expected_total) < 0.01
        print(f"[✓] 金额一致性: 配件¥{parts_cost_in_detail:.2f}+工时¥{order['labor_cost']:.2f}=¥{total_in_detail:.2f}")

        history = WorkOrderService.get_vehicle_history("京T00003")
        assert len(history['orders']) == 1
        assert abs(history['orders'][0]['total_cost'] - expected_total) < 0.01
        print(f"[✓] 维修历史金额同步: ¥{history['orders'][0]['total_cost']:.2f}")

        print("[✓] 测试 3 通过: 工单重新结算功能正常，库存/金额/详情一致")
        return True
    except Exception as e:
        print(f"[✗] 测试 3 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vehicle_overview():
    print("\n" + "=" * 60)
    print("测试 4: 车辆维修概览")
    print("=" * 60)

    try:
        vid, _ = VehicleService.add_vehicle(
            "京T00004", "测试车4", "TVIN0000000000004", 30000
        )
        oil = PartService.find_part_by_code("P001")

        for i in range(6):
            labor = 50 + i * 10
            WorkOrderService.create_work_order(
                vid, 31000 + i * 1000, f"保养{i + 1}", None, labor,
                [{'part_id': oil['id'], 'quantity': 1}]
            )
        print(f"[✓] 创建 6 条工单用于概览测试")

        ok, result = WorkOrderService.get_vehicle_overview("京T00004")
        assert ok, f"概览查询失败: {result}"

        print(f"  累计维修: {result['order_count']} 次")
        print(f"  累计花费: ¥{result['total_spent']:.2f}")
        print(f"  最近5条工单: {len(result['recent_orders'])}")
        print(f"  保养状态: 已行驶{result['mileage_since_maintenance']}km, "
              f"剩余{result['maintenance_remaining']}km")

        assert result['order_count'] == 6, f"工单数量应为6: {result['order_count']}"
        assert result['total_spent'] > 0, "累计花费应>0"
        assert len(result['recent_orders']) == 5, f"最近工单应为5条: {len(result['recent_orders'])}"
        assert result['latest_mileage'] == 36000, f"里程应为36000: {result['latest_mileage']}"

        WorkOrderService.cancel_work_order(result['recent_orders'][0]['id'])
        ok2, result2 = WorkOrderService.get_vehicle_overview("京T00004")
        assert result2['void_count'] == 1
        assert result2['order_count'] == 5
        print(f"[✓] 撤销后概览更新: 有效{result2['order_count']}次, 撤销{result2['void_count']}次")

        ok3, _ = WorkOrderService.get_vehicle_overview("不存在的车牌")
        assert not ok3
        print(f"[✓] 不存在车牌正确返回错误")

        print("[✓] 测试 4 通过: 车辆维修概览功能正常")
        return True
    except Exception as e:
        print(f"[✗] 测试 4 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_purchase_suggestion_flow():
    print("\n" + "=" * 60)
    print("测试 5: 采购建议完整流程 - 生成/处理/状态同步")
    print("=" * 60)

    try:
        ok, res = PartService.add_part("测试缺件A", "SHORT01", 100.00, 2, 10)
        assert ok is not None
        ok, res = PartService.add_part("测试缺件B", "SHORT02", 50.00, 1, 8)
        assert ok is not None
        PartService.stock_out(PartService.find_part_by_code("SHORT01")['id'], 1)
        print(f"[✓] 制造2个低库存配件")

        suggestions = PurchaseSuggestionService.generate_all_suggestions()
        print(f"[✓] 生成待处理采购建议: {len(suggestions)} 条")
        assert len(suggestions) >= 2

        stats = PurchaseSuggestionService.get_suggestion_statistics()
        before_pending = stats['pending_count']
        print(f"  处理前: 待处理{before_pending}, 缺件{stats['pending_parts_count']}种, 预估¥{stats['total_suggested_value']:.2f}")

        target = suggestions[0]
        part_before = PartService.find_part_by_id(target['part_id'])
        stock_before = part_before['stock']

        ok_p, res_p = PurchaseSuggestionService.mark_processed(target['id'], actual_quantity=target['suggested_quantity'])
        assert ok_p, f"处理失败: {res_p}"
        print(f"[✓] 处理1条采购建议: {res_p['part_name']} 入库{res_p['purchased_qty']}件, 新库存{res_p['new_stock']}")

        part_after = PartService.find_part_by_id(target['part_id'])
        assert part_after['stock'] == stock_before + target['suggested_quantity']
        print(f"[✓] 库存同步更新: {stock_before} -> {part_after['stock']}")

        ignore_target = suggestions[1]
        PurchaseSuggestionService.mark_ignored(ignore_target['id'])
        print(f"[✓] 忽略1条采购建议: {ignore_target['part_name']}")

        stats_after = PurchaseSuggestionService.get_suggestion_statistics()
        assert stats_after['pending_count'] == before_pending - 2
        assert stats_after['processed_count'] >= 1
        assert stats_after['ignored_count'] >= 1
        print(f"  处理后: 待处理{stats_after['pending_count']}, 已处理{stats_after['processed_count']}, 已忽略{stats_after['ignored_count']}")
        print(f"  统计同步正确")

        ok_p2, _ = PurchaseSuggestionService.mark_processed(target['id'])
        assert not ok_p2, "重复处理应被拦截"
        print(f"[✓] 重复处理正确拦截")

        print("[✓] 测试 5 通过: 采购建议完整流程正常")
        return True
    except Exception as e:
        print(f"[✗] 测试 5 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_import_export():
    print("\n" + "=" * 60)
    print("测试 6: 配件批量导入导出")
    print("=" * 60)

    try:
        ok, tpl_path = export_parts_template()
        assert ok, f"模板生成失败: {tpl_path}"
        assert os.path.exists(tpl_path)
        print(f"[✓] 导入模板生成: {tpl_path}")

        ok, list_path = export_parts_list()
        assert ok, f"清单导出失败: {list_path}"
        assert os.path.exists(list_path)
        print(f"[✓] 配件清单导出: {list_path}")

        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "配件数据"
        ws.append(["配件名称*", "配件编号*", "单价(元)*", "初始库存", "最小库存量"])
        ws.append(["导入机油", "IMP001", 99.50, 15, 5])
        ws.append(["导入滤芯", "IMP002", 28.00, 30, 5])
        ws.append(["", "IMP003", 50.00, 10, 5])
        ws.append(["错误价格配件", "IMP004", "XXX", 10, 5])
        ws.append(["重复配件", "P001", 10.00, 10, 5])
        ws.append(["负库存配件", "IMP005", 30.00, -5, 5])
        ws.append(["示例配件", "EX999", 10.00, 10, 5])
        test_file = os.path.join(os.path.dirname(DB_PATH), "..", "exports", "test_import.xlsx")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        wb.save(test_file)

        ok_i, err_i, success, failure = import_parts_from_excel(test_file)
        assert ok_i, f"导入失败: {err_i}"
        print(f"\n  导入结果: 成功 {len(success)}, 失败 {len(failure)}")
        if success:
            print("  成功项:")
            for s in success:
                print(f"    行{s['row']}: {s['code']} - {s['name']} x{s['stock']}")
        if failure:
            print("  失败项:")
            for f in failure:
                print(f"    行{f['row']} [{f.get('code','')}]: {';'.join(f['errors'])}")

        success_codes = [s['code'] for s in success]
        failure_codes = [f.get('code', '') for f in failure]
        assert 'IMP001' in success_codes, "IMP001 应成功"
        assert 'IMP002' in success_codes, "IMP002 应成功"
        assert 'IMP003' in failure_codes, "IMP003 应失败(名称空)"
        assert 'IMP004' in failure_codes, "IMP004 应失败(价格非数字)"
        assert 'P001' in failure_codes, "P001 应失败(重复编号)"
        assert 'IMP005' in failure_codes, "IMP005 应失败(负库存)"
        assert 'EX999' not in success_codes and 'EX999' not in failure_codes, "EX999 示例应跳过"

        imp = PartService.find_part_by_code("IMP001")
        assert imp is not None
        assert imp['stock'] == 15
        print(f"\n[✓] IMP001已入库: 库存{imp['stock']}")

        print("[✓] 测试 6 通过: 批量导入导出功能正常，正确区分成功/失败/跳过")
        return True
    except Exception as e:
        print(f"[✗] 测试 6 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    cleanup()
    init_db()
    migrate_db()
    seed_sample_data()

    print("\n🚗 汽车维修管理系统 - 新增功能回归测试")
    print("=" * 60)

    tests = [
        test_delete_vehicle_cascade,
        test_cancel_work_order,
        test_resettle_work_order,
        test_vehicle_overview,
        test_purchase_suggestion_flow,
        test_batch_import_export,
    ]

    passed = 0
    failed = 0
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed == 0:
        print("\n✓ 全部新增功能验证通过！")
        cleanup()
        return 0
    else:
        print("\n✗ 存在测试失败，请检查！")
        return 1


if __name__ == "__main__":
    sys.exit(main())
