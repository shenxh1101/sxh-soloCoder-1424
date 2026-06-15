import os
from services import PartService, WorkOrderService
from datetime import datetime

EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')


def ensure_export_dir():
    os.makedirs(EXPORT_DIR, exist_ok=True)


def export_parts_transactions(start_date=None, end_date=None, filename=None):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    except ImportError:
        return False, "请先安装 openpyxl: pip install openpyxl"

    ensure_export_dir()

    transactions = PartService.list_transactions(start_date, end_date)

    if not filename:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"配件出入库明细_{ts}.xlsx"
    filepath = os.path.join(EXPORT_DIR, filename)

    wb = Workbook()
    ws = wb.active
    ws.title = "出入库明细"

    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    headers = ["日期时间", "配件编号", "配件名称", "类型", "数量", "关联工单", "备注"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    row = 2
    for txn in transactions:
        txn_type = "入库" if txn['type'] == 'IN' else "出库"
        ws.cell(row=row, column=1, value=txn['created_at']).border = thin_border
        ws.cell(row=row, column=2, value=txn.get('part_code', '')).border = thin_border
        ws.cell(row=row, column=3, value=txn.get('part_name', '')).border = thin_border
        ws.cell(row=row, column=4, value=txn_type).border = thin_border
        ws.cell(row=row, column=5, value=txn['quantity']).border = thin_border
        ws.cell(row=row, column=6, value=txn.get('order_id', '') or '').border = thin_border
        ws.cell(row=row, column=7, value=txn.get('note', '') or '').border = thin_border
        row += 1

    for col in range(1, 8):
        ws.column_dimensions[chr(64 + col)].width = 18

    wb.save(filepath)
    return True, filepath


def export_revenue_report(start_date, end_date, filename=None):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    except ImportError:
        return False, "请先安装 openpyxl: pip install openpyxl"

    ensure_export_dir()

    stats = WorkOrderService.get_revenue_statistics(start_date, end_date)

    if not filename:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"维修收入统计_{start_date}_{end_date}.xlsx"
    filepath = os.path.join(EXPORT_DIR, filename)

    wb = Workbook()

    ws_summary = wb.active
    ws_summary.title = "统计汇总"

    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    title_font = Font(bold=True, size=14)
    label_font = Font(bold=True, size=11)
    value_font = Font(size=11)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    ws_summary.merge_cells('A1:D1')
    ws_summary.cell(row=1, column=1, value="维修收入统计报表").font = title_font
    ws_summary.cell(row=1, column=1).alignment = Alignment(horizontal="center")

    ws_summary.cell(row=3, column=1, value="统计期间:").font = label_font
    ws_summary.cell(row=3, column=2, value=f"{start_date} 至 {end_date}").font = value_font

    summary_data = [
        ("工单总数", stats['order_count']),
        ("总收入(元)", f"{stats['total_revenue']:.2f}"),
        ("  工时费(元)", f"{stats['total_labor']:.2f}"),
        ("  配件费(元)", f"{stats['total_parts_cost']:.2f}"),
        ("平均客单价(元)", f"{stats['avg_order_value']:.2f}"),
    ]

    row = 5
    for label, value in summary_data:
        ws_summary.cell(row=row, column=1, value=label).font = label_font
        ws_summary.cell(row=row, column=2, value=value).font = value_font
        row += 1

    for col in range(1, 5):
        ws_summary.column_dimensions[chr(64 + col)].width = 22

    ws_detail = wb.create_sheet("工单明细")

    detail_headers = ["工单号", "日期时间", "车牌号", "品牌型号", "里程(km)", "故障描述",
                      "故障码", "工时费(元)", "配件费(元)", "总费用(元)"]
    for col, header in enumerate(detail_headers, 1):
        cell = ws_detail.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    from repository import WorkOrderPartRepository
    row = 2
    for order in stats['orders']:
        parts = WorkOrderPartRepository.get_by_work_order_id(order['id'])
        parts_cost = sum(p['subtotal'] for p in parts)
        ws_detail.cell(row=row, column=1, value=order['id']).border = thin_border
        ws_detail.cell(row=row, column=2, value=order['created_at']).border = thin_border
        ws_detail.cell(row=row, column=3, value=order.get('plate_number', '')).border = thin_border
        ws_detail.cell(row=row, column=4, value=order.get('brand_model', '')).border = thin_border
        ws_detail.cell(row=row, column=5, value=order['mileage']).border = thin_border
        ws_detail.cell(row=row, column=6, value=order['fault_description']).border = thin_border
        ws_detail.cell(row=row, column=7, value=order.get('fault_code', '') or '').border = thin_border
        ws_detail.cell(row=row, column=8, value=round(order['labor_cost'], 2)).border = thin_border
        ws_detail.cell(row=row, column=9, value=round(parts_cost, 2)).border = thin_border
        ws_detail.cell(row=row, column=10, value=round(order['total_cost'], 2)).border = thin_border
        row += 1

    col_widths = [10, 20, 12, 18, 12, 30, 12, 12, 12, 12]
    for idx, width in enumerate(col_widths, 1):
        ws_detail.column_dimensions[chr(64 + idx)].width = width

    wb.save(filepath)
    return True, filepath


def generate_history_report(plate_number):
    history = WorkOrderService.get_vehicle_history(plate_number)
    if not history:
        return None

    lines = []
    lines.append("=" * 70)
    lines.append("车辆维修历史报告")
    lines.append("=" * 70)
    lines.append("")

    v = history['vehicle']
    lines.append(f"车牌号:    {v['plate_number']}")
    lines.append(f"品牌型号:  {v['brand_model']}")
    lines.append(f"VIN码:     {v['vin_code']}")
    lines.append(f"上次保养里程: {v['last_maintenance_mileage']} km")
    lines.append(f"建档时间:  {v['created_at']}")
    lines.append("")

    orders = history['orders']
    lines.append(f"维修记录总数: {len(orders)} 次")
    lines.append("-" * 70)

    total_cost_all = 0.0
    for idx, order in enumerate(orders, 1):
        lines.append("")
        lines.append(f"【工单 #{order['id']}】 {order['created_at']}")
        lines.append(f"  进厂里程:   {order['mileage']} km")
        lines.append(f"  故障描述:   {order['fault_description']}")
        if order.get('fault_code'):
            lines.append(f"  故障码:     {order['fault_code']} - {order.get('fault_desc', '')}")
        lines.append("")

        parts = order['parts']
        if parts:
            lines.append("  更换配件:")
            lines.append(f"  {'序号':<6}{'配件名称':<16}{'编号':<10}{'单价(元)':<10}{'数量':<6}{'小计(元)':<10}")
            lines.append("  " + "-" * 58)
            for i, p in enumerate(parts, 1):
                lines.append(f"  {i:<6}{p['part_name']:<16}{p['part_code']:<10}"
                             f"{p['unit_price']:<10.2f}{p['quantity']:<6}{p['subtotal']:<10.2f}")

        parts_subtotal = sum(p['subtotal'] for p in parts)
        lines.append("")
        lines.append(f"  配件费用:   {parts_subtotal:.2f} 元")
        lines.append(f"  工时费用:   {order['labor_cost']:.2f} 元")
        lines.append(f"  工单总计:   {order['total_cost']:.2f} 元")
        total_cost_all += order['total_cost']
        lines.append("")
        lines.append("  " + "-" * 58)

    lines.append("")
    lines.append("=" * 70)
    lines.append(f"累计维修总费用: {total_cost_all:.2f} 元")
    lines.append("=" * 70)

    return "\n".join(lines)


def save_history_report(plate_number, filename=None):
    report = generate_history_report(plate_number)
    if not report:
        return False, "未找到该车辆的维修记录"

    ensure_export_dir()
    if not filename:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"维修历史_{plate_number}_{ts}.txt"
    filepath = os.path.join(EXPORT_DIR, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report)

    return True, filepath
