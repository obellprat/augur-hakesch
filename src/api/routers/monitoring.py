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
from typing import Optional, Dict, List
import logging
import time
from threading import Lock, Thread
import atexit
import subprocess

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Cache for CPU stats to avoid blocking on every request
_cpu_cache = {
    "last_update": 0,
    "cpu_percent_overall": 0.0,
    "cpu_percent_per_core": [],
    "cpu_times_percent": {},
    "initialized": False
}
_cpu_cache_lock = Lock()
_cpu_thread_running = False
_cpu_thread = None


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


def _cpu_monitor_thread():
    """Background thread that monitors CPU usage on-demand (not continuously)"""
    global _cpu_cache, _cpu_thread_running
    
    # Establish baseline first - use blocking method initially
    logging.info("CPU monitor: Establishing baseline...")
    psutil.cpu_percent(interval=0.5, percpu=True)
    psutil.cpu_percent(interval=0.5, percpu=False)
    psutil.cpu_times_percent(interval=0.5)
    
    consecutive_errors = 0
    last_valid_reading = None
    
    while _cpu_thread_running:
        try:
            # Use blocking cpu_percent with a short interval for more accurate readings
            # This is more reliable than interval=None especially in containers/WSL
            cpu_percent_per_core = psutil.cpu_percent(interval=1.0, percpu=True)
            cpu_percent_overall = psutil.cpu_percent(interval=None, percpu=False)
            cpu_times_percent_obj = psutil.cpu_times_percent(interval=None)
            
            # Validate readings - if all cores show 100%, it might be a measurement artifact
            is_valid = True
            if cpu_percent_overall >= 99.0 and all(core >= 99.0 for core in cpu_percent_per_core):
                is_valid = False
                consecutive_errors += 1
                # Only log every 10th occurrence to avoid log spam
                if consecutive_errors <= 3 or consecutive_errors % 10 == 0:
                    logging.debug(f"CPU monitor: Skipping suspicious reading (all cores at 100%), count: {consecutive_errors}")
            
            # If we have too many consecutive errors, re-establish baseline
            if consecutive_errors >= 10:
                logging.info("CPU monitor: Re-establishing baseline after repeated suspicious readings...")
                psutil.cpu_percent(interval=1.0, percpu=True)
                psutil.cpu_percent(interval=1.0, percpu=False)
                psutil.cpu_times_percent(interval=1.0)
                consecutive_errors = 0
                continue  # Skip this iteration
            
            if is_valid:
                consecutive_errors = 0
                last_valid_reading = {
                    "overall": cpu_percent_overall,
                    "per_core": cpu_percent_per_core,
                    "times_percent": cpu_times_percent_obj
                }
                
                # Update cache
                with _cpu_cache_lock:
                    _cpu_cache["cpu_percent_overall"] = cpu_percent_overall
                    _cpu_cache["cpu_percent_per_core"] = cpu_percent_per_core
                    _cpu_cache["cpu_times_percent"] = {
                        "user": cpu_times_percent_obj.user,
                        "system": cpu_times_percent_obj.system,
                        "idle": cpu_times_percent_obj.idle
                    }
                    _cpu_cache["last_update"] = time.time()
                    _cpu_cache["initialized"] = True
            else:
                # Use last valid reading if available
                if last_valid_reading:
                    with _cpu_cache_lock:
                        _cpu_cache["cpu_percent_overall"] = last_valid_reading["overall"]
                        _cpu_cache["cpu_percent_per_core"] = last_valid_reading["per_core"]
                        _cpu_cache["cpu_times_percent"] = {
                            "user": last_valid_reading["times_percent"].user,
                            "system": last_valid_reading["times_percent"].system,
                            "idle": last_valid_reading["times_percent"].idle
                        }
                        _cpu_cache["last_update"] = time.time()
                        _cpu_cache["initialized"] = True
            
            # Sleep for 5 seconds before next update (reduced frequency)
            time.sleep(5.0)
        except Exception as e:
            consecutive_errors += 1
            logging.error(f"Error in CPU monitor thread: {e}")
            time.sleep(5.0)


def _start_cpu_monitor():
    """Start the background CPU monitoring thread"""
    global _cpu_thread_running, _cpu_thread
    
    if not _cpu_thread_running:
        _cpu_thread_running = True
        _cpu_thread = Thread(target=_cpu_monitor_thread, daemon=True)
        _cpu_thread.start()
        logging.info("CPU monitoring thread started")


def _stop_cpu_monitor():
    """Stop the background CPU monitoring thread"""
    global _cpu_thread_running
    _cpu_thread_running = False


# Register cleanup on exit (thread starts lazily on first CPU endpoint call)
atexit.register(_stop_cpu_monitor)


@router.get("/cpu")
async def get_cpu_info(user: User = Depends(get_user)):
    """Get CPU usage information"""
    try:
        # Ensure CPU monitor is running
        if not _cpu_thread_running:
            _start_cpu_monitor()
        
        # Get cached values (non-blocking reads)
        with _cpu_cache_lock:
            # If not initialized yet, return zeros to avoid showing 100%
            if not _cpu_cache["initialized"]:
                return JSONResponse({
                    "cpu_percent_overall": 0.0,
                    "cpu_percent_per_core": [0.0] * psutil.cpu_count(logical=True),
                    "cpu_freq": {
                        "current": None,
                        "min": None,
                        "max": None
                    },
                    "cpu_times": {},
                    "cpu_times_percent": {
                        "user": 0.0,
                        "system": 0.0,
                        "idle": 0.0
                    },
                    "load_average": None,
                    "message": "CPU monitoring initializing..."
                })
            
            cpu_percent_overall = _cpu_cache["cpu_percent_overall"]
            cpu_percent_per_core = _cpu_cache["cpu_percent_per_core"]
            cpu_times_percent = _cpu_cache["cpu_times_percent"]
        
        # Get CPU times (non-blocking)
        cpu_times = psutil.cpu_times()
        
        # Get CPU frequency (non-blocking)
        cpu_freq_obj = psutil.cpu_freq()
        
        return JSONResponse({
            "cpu_percent_overall": round(cpu_percent_overall, 1),
            "cpu_percent_per_core": [round(core, 1) for core in cpu_percent_per_core],
            "cpu_freq": {
                "current": round(cpu_freq_obj.current, 0) if cpu_freq_obj else None,
                "min": round(cpu_freq_obj.min, 0) if cpu_freq_obj else None,
                "max": round(cpu_freq_obj.max, 0) if cpu_freq_obj else None
            },
            "cpu_times": {
                "user": cpu_times.user,
                "system": cpu_times.system,
                "idle": cpu_times.idle,
                "nice": getattr(cpu_times, 'nice', None),
                "iowait": getattr(cpu_times, 'iowait', None),
                "irq": getattr(cpu_times, 'irq', None),
                "softirq": getattr(cpu_times, 'softirq', None)
            },
            "cpu_times_percent": {
                "user": round(cpu_times_percent.get("user", 0), 1),
                "system": round(cpu_times_percent.get("system", 0), 1),
                "idle": round(cpu_times_percent.get("idle", 0), 1)
            },
            "load_average": [round(load, 2) for load in os.getloadavg()] if hasattr(os, 'getloadavg') else None
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


def _get_directory_size(path: Path) -> Optional[Dict]:
    """Get directory size using du command (more efficient than recursive walk)"""
    try:
        if not path.exists() or not path.is_dir():
            return None
        
        # Use du command for efficiency (works on Linux/Unix)
        try:
            result = subprocess.run(
                ['du', '-sb', str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            if result.returncode == 0:
                size_bytes = int(result.stdout.split()[0])
                return {
                    "path": str(path),
                    "size_bytes": size_bytes,
                    "size_gb": round(size_bytes / (1024**3), 2),
                    "size_mb": round(size_bytes / (1024**2), 2)
                }
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            # Fallback to recursive walk if du is not available
            pass
        
        # Fallback: recursive directory size calculation
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        continue
        except (OSError, PermissionError):
            return None
        
        return {
            "path": str(path),
            "size_bytes": total_size,
            "size_gb": round(total_size / (1024**3), 2),
            "size_mb": round(total_size / (1024**2), 2)
        }
    except Exception:
        return None


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
        
        # Get data directory usage
        data_directories = []
        possible_data_paths = [
            Path("/usr/src/app/data"),  # Production path
            Path("data"),  # Development path
            Path(os.getenv("DATA_DIR", "data"))  # Environment variable override
        ]
        
        data_path = None
        for path in possible_data_paths:
            if path.exists() and path.is_dir():
                data_path = path
                break
        
        if data_path:
            # Get size of main data directory
            data_dir_info = _get_directory_size(data_path)
            if data_dir_info:
                data_directories.append({
                    "name": "data",
                    "path": str(data_path),
                    "size_gb": data_dir_info["size_gb"],
                    "size_mb": data_dir_info["size_mb"],
                    "size_bytes": data_dir_info["size_bytes"]
                })
            
            # Get sizes of numbered subdirectories (1, 2, 3, ...)
            try:
                for item in sorted(data_path.iterdir()):
                    if item.is_dir() and item.name.isdigit():
                        subdir_info = _get_directory_size(item)
                        if subdir_info:
                            data_directories.append({
                                "name": item.name,
                                "path": str(item),
                                "size_gb": subdir_info["size_gb"],
                                "size_mb": subdir_info["size_mb"],
                                "size_bytes": subdir_info["size_bytes"]
                            })
            except (PermissionError, OSError) as e:
                logging.warning(f"Could not read subdirectories in {data_path}: {e}")
        
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
            "io_counters": disk_io_dict,
            "data_directories": data_directories
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
        # Check for logs directory in production path first, then fall back to relative path
        logs_dir = None
        possible_paths = []
        
        # Add environment variable path if set
        env_logs_dir = os.getenv("LOGS_DIR")
        if env_logs_dir:
            possible_paths.append(Path(env_logs_dir))
        
        # Add production path
        possible_paths.append(Path("/usr/src/app/logs"))
        
        # Add development path (relative)
        possible_paths.append(Path("logs"))
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                logs_dir = path
                break
        
        if logs_dir is None:
            return JSONResponse({
                "logs": [],
                "message": "Logs directory does not exist",
                "checked_paths": [str(p) for p in possible_paths]
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
        # Ensure CPU monitor is running
        if not _cpu_thread_running:
            _start_cpu_monitor()
        
        # Get cached CPU value (non-blocking read)
        with _cpu_cache_lock:
            if not _cpu_cache["initialized"]:
                cpu_percent = 0.0
            else:
                cpu_percent = _cpu_cache["cpu_percent_overall"]
        
        # Get other metrics (all non-blocking)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        return JSONResponse({
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": round(cpu_percent, 1),
                "free_percent": round(100 - cpu_percent, 1)
            },
            "memory": {
                "used_percent": round(mem.percent, 1),
                "free_percent": round(100 - mem.percent, 1),
                "used_gb": round(mem.used / (1024**3), 2),
                "free_gb": round(mem.available / (1024**3), 2),
                "total_gb": round(mem.total / (1024**3), 2)
            },
            "disk": {
                "used_percent": round(disk.percent, 1),
                "free_percent": round(100 - disk.percent, 1),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "total_gb": round(disk.total / (1024**3), 2)
            },
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_formatted": str(uptime).split('.')[0]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting monitoring summary: {str(e)}")
