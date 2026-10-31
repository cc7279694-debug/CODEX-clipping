# Run manually in a normal Windows PowerShell session, without administrator rights.
# Listens only on 127.0.0.1, uses a random ephemeral port, and closes every socket.
$listener = $null
$client = $null
$server = $null
$exitCode = 1
try {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    Write-Host 'LISTEN_PASS'
    $port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
    $accept = $listener.AcceptTcpClientAsync()
    $client = [System.Net.Sockets.TcpClient]::new([System.Net.Sockets.AddressFamily]::InterNetwork)
    $connect = $client.ConnectAsync('127.0.0.1', $port)
    if (-not $connect.Wait(3000)) { throw 'CONNECT_TIMEOUT' }
    if (-not $accept.Wait(3000)) { throw 'ACCEPT_TIMEOUT' }
    $server = $accept.Result
    Write-Host 'CONNECT_PASS'
    $serverStream = $server.GetStream()
    $clientStream = $client.GetStream()
    $serverStream.ReadTimeout = 3000
    $clientStream.ReadTimeout = 3000
    $serverStream.WriteTimeout = 3000
    $clientStream.WriteTimeout = 3000
    $clientStream.WriteByte(42)
    $byte = $serverStream.ReadByte()
    if ($byte -ne 42) { throw 'DATA_SEND_MISMATCH' }
    $serverStream.WriteByte([byte]$byte)
    if ($clientStream.ReadByte() -ne 42) { throw 'DATA_RETURN_MISMATCH' }
    Write-Host 'DATA_ROUNDTRIP_PASS'
    $exitCode = 0
} catch {
    Write-Host ('FAILED: ' + $_.Exception.Message)
} finally {
    if ($null -ne $server) { $server.Dispose() }
    if ($null -ne $client) { $client.Dispose() }
    if ($null -ne $listener) { $listener.Stop() }
}
exit $exitCode
