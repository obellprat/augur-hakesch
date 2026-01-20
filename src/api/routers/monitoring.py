from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from helpers.user import get_user
from prisma.models import User
import psutil
import platform
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import logging

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/system")
async def get_system_info(user: User = Depends(get_user)):
    """Get basic system information"""
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        return JSONResponse({
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "python_version_info": {
                "major": sys.version_info.major,
                "minor": sys.version_info.minor,
                "micro": sys.version_info.micro
            },
            "boot_time": boot_time.isoformat(),
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_formatted": str(uptime).split('.')[0],  # Remove microseconds
            "hostname": platform.node(),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "cpu_count_logical": psutil.cpu_count(logical=True)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting system info: {str(e)}")


@router.get("/cpu")
async def get_cpu_info(user: User = Depends(get_user)):
    """Get CPU usage information"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        cpu_percent_overall = psutil.cpu_percent(interval=1)
        
        return JSONResponse({
            "cpu_percent_overall": cpu_percent_overall,
            "cpu_percent_per_core": cpu_percent,
            "cpu_freq": {
                "current": psutil.cpu_freq().current if psutil.cpu_freq() else None,
                "min": psutil.cpu_freq().min if psutil.cpu_freq() else None,
                "max": psutil.cpu_freq().max if psutil.cpu_freq() else None
            },
            "cpu_times": {
                "user": psutil.cpu_times().user,
                "system": psutil.cpu_times().system,
                "idle": psutil.cpu_times().idle,
                "nice": getattr(psutil.cpu_times(), 'nice', None),
                "iowait": getattr(psutil.cpu_times(), 'iowait', None),
                "irq": getattr(psutil.cpu_times(), 'irq', None),
                "softirq": getattr(psutil.cpu_times(), 'softirq', None)
            },
            "cpu_times_percent": {
                "user": psutil.cpu_times_percent(interval=1).user,
                "system": psutil.cpu_times_percent(interval=1).system,
                "idle": psutil.cpu_times_percent(interval=1).idle
            },
            "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting CPU info: {str(e)}")


@router.get("/memory")
async def get_memory_info(user: User = Depends(get_user)):
    """Get memory usage information"""
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return JSONResponse({
            "virtual_memory": {
                "total": mem.total,
                "available": mem.available,
                "used": mem.used,
                "free": mem.free,
                "percent": mem.percent,
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "free_gb": round(mem.free / (1024**3), 2)
            },
            "swap_memory": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent,
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "free_gb": round(swap.free / (1024**3), 2)
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting memory info: {str(e)}")


@router.get("/disk")
async def get_disk_info(user: User = Depends(get_user)):
    """Get disk usage information"""
    try:
        disk_usage = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        disk_partitions = []
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_partitions.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "opts": partition.opts,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2)
                })
            except PermissionError:
                # Skip partitions we don't have permission to access
                continue
        
        disk_io_dict = None
        if disk_io:
            disk_io_dict = {
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count,
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes,
                "read_time": disk_io.read_time,
                "write_time": disk_io.write_time,
                "read_bytes_gb": round(disk_io.read_bytes / (1024**3), 2),
                "write_bytes_gb": round(disk_io.write_bytes / (1024**3), 2)
            }
        
        return JSONResponse({
            "root": {
                "total": disk_usage.total,
                "used": disk_usage.used,
                "free": disk_usage.free,
                "percent": disk_usage.percent,
                "total_gb": round(disk_usage.total / (1024**3), 2),
                "used_gb": round(disk_usage.used / (1024**3), 2),
                "free_gb": round(disk_usage.free / (1024**3), 2)
            },
            "partitions": disk_partitions,
            "io_counters": disk_io_dict
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting disk info: {str(e)}")


@router.get("/network")
async def get_network_info(user: User = Depends(get_user)):
    """Get network information"""
    try:
        net_io = psutil.net_io_counters()
        net_connections = len(psutil.net_connections(kind='inet'))
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()
        
        interfaces = []
        for interface_name, addrs in net_if_addrs.items():
            stats = net_if_stats.get(interface_name)
            interfaces.append({
                "name": interface_name,
                "addresses": [
                    {
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast
                    }
                    for addr in addrs
                ],
                "is_up": stats.isup if stats else None,
                "speed": stats.speed if stats else None,
                "mtu": stats.mtu if stats else None
            })
        
        net_io_dict = None
        if net_io:
            net_io_dict = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout,
                "bytes_sent_gb": round(net_io.bytes_sent / (1024**3), 2),
                "bytes_recv_gb": round(net_io.bytes_recv / (1024**3), 2)
            }
        
        return JSONResponse({
            "io_counters": net_io_dict,
            "connections_count": net_connections,
            "interfaces": interfaces
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting network info: {str(e)}")


@router.get("/processes")
async def get_processes_info(user: User = Depends(get_user), limit: int = 10):
    """Get top processes by CPU usage"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'memory_info', 'status', 'create_time']):
            try:
                pinfo = proc.info
                create_time = datetime.fromtimestamp(pinfo['create_time'])
                processes.append({
                    "pid": pinfo['pid'],
                    "name": pinfo['name'],
                    "username": pinfo['username'],
                    "cpu_percent": pinfo['cpu_percent'],
                    "memory_percent": pinfo['memory_percent'],
                    "memory_rss": pinfo['memory_info'].rss if pinfo['memory_info'] else None,
                    "memory_vms": pinfo['memory_info'].vms if pinfo['memory_info'] else None,
                    "status": pinfo['status'],
                    "create_time": create_time.isoformat(),
                    "uptime_seconds": int((datetime.now() - create_time).total_seconds())
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort by CPU usage and return top N
        processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
        
        return JSONResponse({
            "processes": processes[:limit],
            "total_processes": len(processes)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting processes info: {str(e)}")


@router.get("/logs")
async def get_logs(
    user: User = Depends(get_user),
    lines: int = 100,
    log_file: Optional[str] = None
):
    """Get application logs"""
    try:
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return JSONResponse({
                "logs": [],
                "message": "Logs directory does not exist"
            })
        
        # Default to celery.log if no file specified
        if log_file is None:
            log_file = "celery.log"
        
        log_path = logs_dir / log_file
        if not log_path.exists():
            raise HTTPException(status_code=404, detail=f"Log file {log_file} not found")
        
        # Read last N lines
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        # List available log files
        available_logs = [f.name for f in logs_dir.iterdir() if f.is_file() and f.suffix == '.log']
        
        return JSONResponse({
            "logs": last_lines,
            "total_lines": len(all_lines),
            "returned_lines": len(last_lines),
            "log_file": log_file,
            "available_logs": available_logs
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")


@router.get("/summary")
async def get_monitoring_summary(user: User = Depends(get_user)):
    """Get a summary of all monitoring metrics"""
    try:
        # Get all metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        return JSONResponse({
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "free_percent": 100 - cpu_percent
            },
            "memory": {
                "used_percent": mem.percent,
                "free_percent": 100 - mem.percent,
                "used_gb": round(mem.used / (1024**3), 2),
                "free_gb": round(mem.available / (1024**3), 2),
                "total_gb": round(mem.total / (1024**3), 2)
            },
            "disk": {
                "used_percent": disk.percent,
                "free_percent": 100 - disk.percent,
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "total_gb": round(disk.total / (1024**3), 2)
            },
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_formatted": str(uptime).split('.')[0]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting monitoring summary: {str(e)}")
